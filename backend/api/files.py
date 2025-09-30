"""
Agent-Chat Files API V2
Enhanced file upload and management with elegant storage
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Request, Query
from fastapi.responses import StreamingResponse, FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import pandas as pd
from io import BytesIO
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, delete
from core.database import get_db
from models import UploadedFile, WorksheetData, WorksheetRow, FileAccessLog
from services.unified_storage import unified_storage as storage_service
import aiofiles
import mimetypes
from services.azure_sync import azure_sync_service
from core.config import settings

router = APIRouter()


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int
    content_type: str
    status: str
    uploaded_at: datetime
    file_hash: str
    category: str
    metadata: Dict[str, Any] = {}


class FileInfo(BaseModel):
    file_id: str
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    file_path: str
    file_hash: str
    category: str
    status: str
    upload_source: str
    created_at: datetime
    processed_at: Optional[datetime]
    last_accessed: Optional[datetime]
    metadata: Dict[str, Any]
    worksheets: List[Dict[str, Any]] = []


class FileListResponse(BaseModel):
    files: List[FileInfo]
    total: int
    page: int
    size: int
    pages: int


class StorageStatsResponse(BaseModel):
    total_files: int
    total_size: int
    categories: Dict[str, Dict[str, int]]
    storage_path: str


async def log_file_access(
    db: AsyncSession,
    file_id: str,
    access_type: str,
    request: Request,
    user_id: Optional[int] = None
):
    """Log file access for security and analytics"""
    try:
        access_log = FileAccessLog(
            id=str(uuid.uuid4()),
            file_id=file_id,
            access_type=access_type,
            user_id=user_id,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown")
        )
        db.add(access_log)
        await db.commit()
    except Exception:
        pass  # Silent failure for logging


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_single_file(
    request: Request,
    file: UploadFile = File(...),
    process_immediately: bool = Form(True),
    upload_source: str = Form("web_ui"),
    db: AsyncSession = Depends(get_db)
) -> FileUploadResponse:
    """Upload a single file with enhanced validation and storage"""
    try:
        # Validate file type
        allowed_types = ['.xlsx', '.csv', '.json', '.parquet', '.xls']
        if not file.filename or '.' not in file.filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename - no file extension detected"
            )

        file_extension = '.' + file.filename.split('.')[-1].lower()
        if file_extension not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_extension} not allowed. Allowed types: {allowed_types}"
            )

        # Validate file size
        if file.size and file.size > 100 * 1024 * 1024:  # 100MB
            raise HTTPException(
                status_code=400,
                detail="File size exceeds 100MB limit"
            )

        # Generate file ID
        file_id = str(uuid.uuid4())

        # Store file using storage service
        file_info = await storage_service.store_file(
            file,
            file_id,
            metadata={
                "upload_source": upload_source,
                "original_size": file.size,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )

        # Check for duplicate files by hash
        duplicate_check = await db.execute(
            select(UploadedFile).where(UploadedFile.file_hash == file_info["file_hash"])
        )
        existing_file = duplicate_check.scalar_one_or_none()

        if existing_file:
            # File already exists - delete the newly uploaded file and return existing file info
            await storage_service.delete_file(file_info["file_path"])

            raise HTTPException(
                status_code=409,
                detail={
                    "error": "File already exists",
                    "message": f"A file with identical content already exists: {existing_file.filename}",
                    "existing_file": {
                        "file_id": existing_file.id,
                        "filename": existing_file.filename,
                        "uploaded_at": existing_file.created_at.isoformat() if existing_file.created_at else None,
                        "file_size": existing_file.file_size
                    }
                }
            )

        # Create database record
        db_file = UploadedFile(
            id=file_id,
            filename=file.filename,
            original_filename=file.filename,
            file_size=file_info["file_size"],
            content_type=file.content_type,
            file_path=file_info["file_path"],
            file_hash=file_info["file_hash"],
            category=file_info["category"],
            status="uploaded",
            upload_source=upload_source,
            meta_data=file_info["metadata"]
        )

        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)

        # Process file in background if requested
        if process_immediately:
            # Create a background task for processing
            # This avoids database context issues
            import asyncio
            asyncio.create_task(
                process_file_background(
                    file_id=file_id,
                    file_path=file_info["file_path"],
                    filename=file.filename,
                    is_azure=storage_service.is_azure
                )
            )

        # Log access
        await log_file_access(db, file_id, "upload", request)

        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            size=file_info["file_size"],
            content_type=file.content_type,
            status=db_file.status,
            uploaded_at=db_file.created_at,
            file_hash=file_info["file_hash"],
            category=file_info["category"],
            metadata=file_info["metadata"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/files/upload-multiple", response_model=List[FileUploadResponse])
async def upload_multiple_files(
    request: Request,
    files: List[UploadFile] = File(...),
    process_immediately: bool = Form(True),
    upload_source: str = Form("web_ui"),
    db: AsyncSession = Depends(get_db)
) -> List[FileUploadResponse]:
    """Upload multiple files efficiently"""
    results = []
    
    for file in files:
        try:
            # Use the single file upload logic
            result = await upload_single_file(
                request, file, process_immediately, upload_source, db
            )
            results.append(result)
        except HTTPException as e:
            # Create error response for failed files
            error_response = FileUploadResponse(
                file_id=str(uuid.uuid4()),
                filename=file.filename or "unknown",
                size=0,
                content_type=file.content_type or "unknown",
                status="error",
                uploaded_at=datetime.utcnow(),
                file_hash="",
                category="error",
                metadata={"error": e.detail}
            )
            results.append(error_response)
    
    return results


@router.get("/files", response_model=FileListResponse)
async def list_files(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sync_azure: bool = Query(True, description="Sync with Azure before listing"),
    db: AsyncSession = Depends(get_db)
) -> FileListResponse:
    """List uploaded files with filtering and pagination"""
    try:
        # Sync with Azure if using Azure storage and sync is requested
        if settings.storage_backend == 'azure' and sync_azure:
            try:
                import logging
                logging.info("Syncing files from Azure Blob Storage before listing...")
                sync_result = await azure_sync_service.sync_azure_to_database(db)
                if sync_result['status'] == 'error':
                    import logging
                    logging.error(f"Azure sync failed: {sync_result.get('error', 'Unknown error')}")
                else:
                    import logging
                    logging.info(f"Azure sync completed: {sync_result.get('added', 0)} files added")
            except Exception as e:
                import logging
                logging.error(f"Failed to sync with Azure: {str(e)}")
                # Continue without sync - don't fail the request
        # Build query
        query = select(UploadedFile)
        
        # Apply filters
        if category:
            query = query.where(UploadedFile.category == category)
        
        if status:
            query = query.where(UploadedFile.status == status)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    UploadedFile.filename.ilike(search_term),
                    UploadedFile.original_filename.ilike(search_term)
                )
            )
        
        # Get total count
        count_query = select(func.count(UploadedFile.id)).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        offset = (page - 1) * size
        query = query.order_by(desc(UploadedFile.created_at)).offset(offset).limit(size)
        
        result = await db.execute(query)
        files = result.scalars().all()
        
        # Convert to response format
        file_list = []
        for file in files:
            # Get worksheet count
            worksheet_query = select(func.count(WorksheetData.id)).where(WorksheetData.file_id == file.id)
            worksheet_result = await db.execute(worksheet_query)
            worksheet_count = worksheet_result.scalar()
            
            file_info = FileInfo(
                file_id=file.id,
                filename=file.filename,
                original_filename=file.original_filename,
                file_size=file.file_size,
                content_type=file.content_type,
                file_path=file.file_path,
                file_hash=file.file_hash,
                category=file.category,
                status=file.status,
                upload_source=file.upload_source,
                created_at=file.created_at,
                processed_at=file.processed_at,
                last_accessed=file.last_accessed,
                metadata={**file.meta_data, "worksheet_count": worksheet_count}
            )
            file_list.append(file_info)
        
        pages = (total + size - 1) // size
        
        return FileListResponse(
            files=file_list,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/files/{file_id}", response_model=FileInfo)
async def get_file_info(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> FileInfo:
    """Get detailed file information"""
    try:
        # Get file record
        result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
        file_record = result.scalar_one_or_none()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get worksheets
        worksheets_result = await db.execute(
            select(WorksheetData).where(WorksheetData.file_id == file_id)
        )
        worksheets = worksheets_result.scalars().all()
        
        # Update last accessed time
        file_record.last_accessed = datetime.utcnow()
        await db.commit()
        
        # Log access
        await log_file_access(db, file_id, "info", request)
        
        worksheet_info = [
            {
                "worksheet_id": ws.id,
                "sheet_name": ws.sheet_name,
                "sheet_index": ws.sheet_index,
                "row_count": ws.row_count,
                "column_count": ws.column_count,
                "column_headers": ws.column_headers,
                "data_types": ws.data_types,
                "data_summary": ws.data_summary
            }
            for ws in worksheets
        ]
        
        return FileInfo(
            file_id=file_record.id,
            filename=file_record.filename,
            original_filename=file_record.original_filename,
            file_size=file_record.file_size,
            content_type=file_record.content_type,
            file_path=file_record.file_path,
            file_hash=file_record.file_hash,
            category=file_record.category,
            status=file_record.status,
            upload_source=file_record.upload_source,
            created_at=file_record.created_at,
            processed_at=file_record.processed_at,
            last_accessed=file_record.last_accessed,
            metadata=file_record.meta_data,
            worksheets=worksheet_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Download file with streaming support for both local and Azure storage"""
    try:
        # Get file record
        result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
        file_record = result.scalar_one_or_none()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Update last accessed time
        file_record.last_accessed = datetime.utcnow()
        await db.commit()
        
        # Log access
        await log_file_access(db, file_id, "download", request)
        
        # Get media type
        media_type = file_record.content_type or "application/octet-stream"
        
        # Handle based on storage backend
        if storage_service.is_local:
            # For local storage, get the file path
            file_path = await storage_service.get_file(file_record.file_path)
            if not file_path:
                raise HTTPException(status_code=404, detail="File not found in storage")
            
            return FileResponse(
                path=str(file_path),
                filename=file_record.original_filename,
                media_type=media_type
            )
        else:
            # For Azure storage, stream the file
            file_stream = await storage_service.get_file_stream(file_record.file_path)
            if not file_stream:
                raise HTTPException(status_code=404, detail="File not found in storage")
            
            # Create streaming response
            return StreamingResponse(
                file_stream,
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename=\"{file_record.original_filename}\""
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Delete file from storage and database"""
    try:
        # Get file record
        result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
        file_record = result.scalar_one_or_none()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        # First, delete all related file access logs to avoid foreign key constraint
        await db.execute(
            delete(FileAccessLog).where(FileAccessLog.file_id == file_id)
        )

        # Delete from storage
        await storage_service.delete_file(file_record.file_path)

        # Delete from database (cascade will handle worksheets and rows)
        await db.delete(file_record)
        await db.commit()

        # Note: We don't log the delete access since we're deleting the file
        # and all its access logs anyway

        return {"status": "success", "message": f"File {file_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/files/{file_id}/download-url")
async def get_download_url(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    expiry_days: int = Query(7, ge=1, le=30)
):
    """
    Get a direct download URL for a file
    - For Azure: Returns a SAS URL with temporary access
    - For Local: Returns the download endpoint URL
    """
    try:
        # Get file record
        result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
        file_record = result.scalar_one_or_none()
        
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Log access
        await log_file_access(db, file_id, "download_url", request)
        
        # Generate download URL based on storage backend
        if storage_service.is_azure:
            # For Azure, generate SAS URL
            download_url = await storage_service.generate_download_url(
                file_record.file_path,
                expiry_days
            )
            if not download_url:
                raise HTTPException(status_code=500, detail="Failed to generate download URL")
            
            return {
                "download_url": download_url,
                "expires_in_days": expiry_days,
                "storage_backend": "azure"
            }
        else:
            # For local storage, return the API download endpoint
            base_url = str(request.base_url).rstrip('/')
            download_url = f"{base_url}/api/v1/files/{file_id}/download"
            
            return {
                "download_url": download_url,
                "expires_in_days": None,
                "storage_backend": "local"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")


@router.get("/files/storage/stats", response_model=StorageStatsResponse)
async def get_storage_stats() -> StorageStatsResponse:
    """Get storage statistics"""
    try:
        stats = await storage_service.get_storage_stats()
        return StorageStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get storage stats: {str(e)}")


@router.post("/files/sync/azure")
async def sync_azure_storage(
    request: Request,
    full_sync: bool = Query(True, description="Perform full bidirectional sync"),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger Azure Blob Storage synchronization.
    This ensures all files in Azure are reflected in the database.
    """
    try:
        if settings.storage_backend != 'azure':
            return {
                "status": "skipped",
                "message": "Not using Azure storage backend",
                "storage_backend": settings.storage_backend
            }
        
        import logging
        logging.info(f"Manual Azure sync triggered (full_sync={full_sync})")
        
        if full_sync:
            result = await azure_sync_service.full_sync(db)
        else:
            result = await azure_sync_service.sync_azure_to_database(db)
        
        # Log the sync operation
        await log_file_access(db, "SYNC", "azure_sync", request)
        
        return {
            "status": result.get('status', 'unknown'),
            "result": result,
            "message": f"Azure sync completed successfully"
        }
    
    except Exception as e:
        import logging
        logging.error(f"Azure sync failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Azure sync failed: {str(e)}")


@router.get("/files/sync/status")
async def get_sync_status(db: AsyncSession = Depends(get_db)):
    """Get the current sync status and statistics"""
    try:
        if settings.storage_backend != 'azure':
            return {
                "storage_backend": settings.storage_backend,
                "sync_enabled": False,
                "message": "Azure sync not applicable for local storage"
            }
        
        # Get counts from both sources
        azure_files = await storage_service.list_files()
        db_result = await db.execute(select(func.count(UploadedFile.id)))
        db_count = db_result.scalar()
        
        return {
            "storage_backend": "azure",
            "sync_enabled": True,
            "azure_files_count": len(azure_files),
            "database_files_count": db_count,
            "in_sync": len(azure_files) == db_count,
            "message": "Files are synchronized" if len(azure_files) == db_count else f"Sync needed: {len(azure_files)} in Azure, {db_count} in database"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")


async def process_file_background(
    file_id: str,
    file_path: str,
    filename: str,
    is_azure: bool
):
    """
    Background task to process uploaded files
    This runs in a separate context to avoid database transaction issues
    """
    import tempfile
    import os
    from core.database import get_db
    
    try:
        # Get a fresh database session for background processing
        async for db in get_db():
            # Get the file record
            from sqlalchemy import select
            result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
            file_record = result.scalar_one_or_none()
            
            if not file_record:
                return
            
            temp_file_path = None
            
            try:
                # For Azure storage, download the file first
                if is_azure:
                    file_content = await storage_service.get_file(file_path)
                    if file_content:
                        # Save to temporary file for processing
                        suffix = f".{filename.split('.')[-1]}" if '.' in filename else ""
                        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                            tmp_file.write(file_content)
                            temp_file_path = tmp_file.name
                        
                        # Process the temporary file
                        await process_file_data(db, file_id, temp_file_path)
                    else:
                        raise Exception("Could not download file from Azure for processing")
                else:
                    # Local storage - process directly
                    # For local storage, file_path should be the absolute path
                    local_path = await storage_service.get_file(file_path)
                    if local_path:
                        await process_file_data(db, file_id, str(local_path))
                    else:
                        raise Exception("Could not find local file for processing")
                
                # Update file status to processed
                file_record.status = "processed"
                file_record.processed_at = datetime.utcnow()
                await db.commit()
                
            except Exception as e:
                # Update file status to error
                file_record.status = "processing_error"
                if not file_record.meta_data:
                    file_record.meta_data = {}
                file_record.meta_data["processing_error"] = str(e)
                await db.commit()
                
                # Log the error for debugging
                import logging
                logging.error(f"Error processing file {file_id}: {str(e)}")
            
            finally:
                # Clean up temporary file if created
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            
            break  # Exit the async for loop
            
    except Exception as e:
        # Log any unexpected errors
        import logging
        logging.error(f"Background processing failed for file {file_id}: {str(e)}")


async def process_file_data(db: AsyncSession, file_id: str, file_path: str):
    """Process file and extract data to database"""
    try:
        # Detect file type
        extension = file_path.split('.')[-1].lower()
        
        if extension in ['xlsx', 'xls']:
            # Process Excel file
            excel_file = pd.ExcelFile(file_path)
            
            for sheet_index, sheet_name in enumerate(excel_file.sheet_names):
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Create worksheet record
                worksheet_id = str(uuid.uuid4())
                worksheet = WorksheetData(
                    id=worksheet_id,
                    file_id=file_id,
                    sheet_name=sheet_name,
                    sheet_index=sheet_index,
                    row_count=len(df),
                    column_count=len(df.columns),
                    column_headers=df.columns.tolist(),
                    data_types=df.dtypes.astype(str).to_dict(),
                    sample_data=df.head(5).to_dict('records'),
                    data_summary=df.describe().to_dict() if not df.empty else {}
                )
                
                db.add(worksheet)
                await db.flush()
                
                # Store rows (limit to prevent excessive memory usage)
                max_rows = 10000  # Configurable limit
                for row_index, (_, row) in enumerate(df.iterrows()):
                    if row_index >= max_rows:
                        break
                        
                    # Convert row to JSON-serializable format
                    row_data = {}
                    for col, value in row.items():
                        if pd.isna(value):
                            row_data[col] = None
                        elif isinstance(value, (pd.Timestamp, datetime)):
                            row_data[col] = value.isoformat()
                        elif hasattr(value, 'item'):  # numpy types
                            row_data[col] = value.item()
                        else:
                            row_data[col] = value
                    
                    worksheet_row = WorksheetRow(
                        id=str(uuid.uuid4()),
                        worksheet_id=worksheet_id,
                        row_index=row_index,
                        row_data=row_data
                    )
                    db.add(worksheet_row)
        
        elif extension == 'csv':
            # Process CSV file
            df = pd.read_csv(file_path)
            
            worksheet_id = str(uuid.uuid4())
            worksheet = WorksheetData(
                id=worksheet_id,
                file_id=file_id,
                sheet_name="Sheet1",
                sheet_index=0,
                row_count=len(df),
                column_count=len(df.columns),
                column_headers=df.columns.tolist(),
                data_types=df.dtypes.astype(str).to_dict(),
                sample_data=df.head(5).to_dict('records'),
                data_summary=df.describe().to_dict() if not df.empty else {}
            )
            
            db.add(worksheet)
            await db.flush()
            
            # Store rows with limit
            max_rows = 10000
            for row_index, (_, row) in enumerate(df.iterrows()):
                if row_index >= max_rows:
                    break
                    
                row_data = {}
                for col, value in row.items():
                    if pd.isna(value):
                        row_data[col] = None
                    elif isinstance(value, (pd.Timestamp, datetime)):
                        row_data[col] = value.isoformat()
                    elif hasattr(value, 'item'):
                        row_data[col] = value.item()
                    else:
                        row_data[col] = value
                
                worksheet_row = WorksheetRow(
                    id=str(uuid.uuid4()),
                    worksheet_id=worksheet_id,
                    row_index=row_index,
                    row_data=row_data
                )
                db.add(worksheet_row)
        
        await db.commit()
        
    except Exception as e:
        await db.rollback()
        raise Exception(f"Failed to process file data: {str(e)}")
