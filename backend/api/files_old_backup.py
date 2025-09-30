"""
Agent-Chat Files API
File upload and management endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import pandas as pd
from io import BytesIO
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db, AsyncSessionLocal
from models import UploadedFile, WorksheetData, WorksheetRow

router = APIRouter()


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int
    content_type: str
    status: str
    uploaded_at: datetime
    metadata: Dict[str, Any] = {}


class FileProcessingResult(BaseModel):
    file_id: str
    status: str  # 'success' or 'error'
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: float
    agent_results: Optional[Dict[str, Any]] = None


@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    process_immediately: bool = Form(False),
    db: AsyncSession = Depends(get_db)
) -> FileUploadResponse:
    """Upload a single file"""
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

        # Read file content
        content = await file.read()

        # Validate file content
        if not content:
            raise HTTPException(
                status_code=400,
                detail="File is empty or corrupted"
            )

        # Create file record in database
        file_id = str(uuid.uuid4())
        db_file = UploadedFile(
            id=file_id,
            filename=file.filename,
            original_filename=file.filename,
            file_size=len(content),
            content_type=file.content_type,
            file_content=content,  # Store actual file content
            status="uploaded",
            meta_data={
                "extension": file_extension,
                "original_filename": file.filename
            }
        )

        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)

        # Process file if requested
        if process_immediately:
            try:
                processing_result = await process_and_store_file_data(db, file_id, content, file.filename)
                db_file.status = "processed"
                db_file.processed_at = datetime.utcnow()
                db_file.meta_data["processing_result"] = processing_result.dict()
            except Exception as e:
                db_file.status = "processing_error"
                db_file.meta_data["processing_error"] = str(e)

            await db.commit()

        # Return response
        file_record = FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            size=len(content),
            content_type=file.content_type,
            status=db_file.status,
            uploaded_at=db_file.created_at,
            metadata=db_file.meta_data
        )

        return file_record

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/files/upload-multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    process_immediately: bool = Form(True),  # Process by default
    db: AsyncSession = Depends(get_db)
) -> List[FileUploadResponse]:
    """Upload multiple files"""
    results = []

    for file in files:
        try:
            # Create a new database session for each file to avoid transaction conflicts
            async with AsyncSessionLocal() as file_db:
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

                # Read file content
                content = await file.read()

                # Validate file content
                if not content:
                    raise HTTPException(
                        status_code=400,
                        detail="File is empty or corrupted"
                    )

                # Create file record in database
                file_id = str(uuid.uuid4())
                db_file = UploadedFile(
                    id=file_id,
                    filename=file.filename,
                    original_filename=file.filename,
                    file_size=len(content),
                    content_type=file.content_type,
                    file_content=content,  # Store actual file content
                    status="uploaded",
                    meta_data={
                        "extension": file_extension,
                        "original_filename": file.filename
                    }
                )

                file_db.add(db_file)
                await file_db.commit()
                await file_db.refresh(db_file)

                # Process file if requested
                if process_immediately:
                    try:
                        processing_result = await process_and_store_file_data(file_db, file_id, content, file.filename)
                        db_file.status = "processed"
                        db_file.processed_at = datetime.utcnow()
                        db_file.meta_data["processing_result"] = processing_result.dict()
                    except Exception as e:
                        db_file.status = "processing_error"
                        db_file.meta_data["processing_error"] = str(e)

                    await file_db.commit()

                # Create response
                result = FileUploadResponse(
                    file_id=file_id,
                    filename=file.filename,
                    size=len(content),
                    content_type=file.content_type,
                    status=db_file.status,
                    uploaded_at=db_file.created_at,
                    metadata=db_file.meta_data
                )
                results.append(result)

        except HTTPException as e:
            # Create error record for HTTP exceptions
            error_record = FileUploadResponse(
                file_id=str(uuid.uuid4()),
                filename=file.filename,
                size=0,
                content_type=file.content_type or "unknown",
                status="error",
                uploaded_at=datetime.utcnow(),
                metadata={"error": e.detail}
            )
            results.append(error_record)
        except Exception as e:
            # Create error record for other exceptions
            error_record = FileUploadResponse(
                file_id=str(uuid.uuid4()),
                filename=file.filename,
                size=0,
                content_type=file.content_type or "unknown",
                status="error",
                uploaded_at=datetime.utcnow(),
                metadata={"error": str(e)}
            )
            results.append(error_record)

    return results


@router.post("/files/{file_id}/process")
async def process_file(file_id: str) -> FileProcessingResult:
    """Process an uploaded file"""
    try:
        # In a real implementation, retrieve file content from storage
        # For now, simulate processing

        start_time = datetime.utcnow()

        # Simulate file processing
        processing_result = FileProcessingResult(
            file_id=file_id,
            status="success",
            data={
                "rows_processed": 1000,
                "columns_detected": 15,
                "data_quality_score": 0.95
            },
            processing_time=(datetime.utcnow() - start_time).total_seconds()
        )

        return processing_result

    except Exception as e:
        return FileProcessingResult(
            file_id=file_id,
            status="error",
            error=str(e),
            processing_time=0.0
        )


async def process_and_store_file_data(db: AsyncSession, file_id: str, content: bytes, filename: str) -> FileProcessingResult:
    """Process file content and store extracted data in database"""
    try:
        start_time = datetime.utcnow()

        # Detect file type and process accordingly
        file_extension = '.' + filename.split('.')[-1].lower()

        if file_extension in ['.xlsx', '.xls']:
            # Process Excel file - potentially multiple sheets
            excel_file = pd.ExcelFile(BytesIO(content))

            data_info = {
                "file_type": "excel",
                "total_sheets": len(excel_file.sheet_names),
                "sheet_names": excel_file.sheet_names,
                "sheets_processed": []
            }

            for sheet_index, sheet_name in enumerate(excel_file.sheet_names):
                df = pd.read_excel(BytesIO(content), sheet_name=sheet_name)

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
                    data_types=df.dtypes.astype(str).to_dict()
                )

                db.add(worksheet)
                await db.flush()  # Get the ID without committing

                # Store each row of data
                for row_index, (_, row) in enumerate(df.iterrows()):
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

                data_info["sheets_processed"].append({
                    "sheet_name": sheet_name,
                    "rows": len(df),
                    "columns": len(df.columns),
                    "worksheet_id": worksheet_id
                })

        elif file_extension == '.csv':
            # Process CSV file
            df = pd.read_csv(BytesIO(content))

            # Create single worksheet for CSV
            worksheet_id = str(uuid.uuid4())
            worksheet = WorksheetData(
                id=worksheet_id,
                file_id=file_id,
                sheet_name="Sheet1",  # Default name for CSV
                sheet_index=0,
                row_count=len(df),
                column_count=len(df.columns),
                column_headers=df.columns.tolist(),
                data_types=df.dtypes.astype(str).to_dict()
            )

            db.add(worksheet)
            await db.flush()

            # Store each row of data
            for row_index, (_, row) in enumerate(df.iterrows()):
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

            data_info = {
                "file_type": "csv",
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "data_types": df.dtypes.astype(str).to_dict(),
                "worksheet_id": worksheet_id
            }

        else:
            data_info = {
                "file_type": "other",
                "size": len(content),
                "message": "File uploaded but content analysis not available for this type"
            }

        # Commit all the data
        await db.commit()

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return FileProcessingResult(
            file_id=file_id,
            status="success",
            data=data_info,
            processing_time=processing_time
        )

    except Exception as e:
        # Rollback in case of error
        await db.rollback()
        return FileProcessingResult(
            file_id=file_id,
            status="error",
            error=str(e),
            processing_time=0.0
        )


@router.get("/files")
async def list_files():
    """List uploaded files"""
    # In a real implementation, retrieve from database
    return {
        "status": "success",
        "files": [],
        "message": "File listing functionality will be implemented with database integration"
    }


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """Delete an uploaded file"""
    # In a real implementation, remove from storage and database
    return {
        "status": "success",
        "message": f"File {file_id} marked for deletion"
    }


@router.get("/files/{file_id}/info")
async def get_file_info(file_id: str, db: AsyncSession = Depends(get_db)):
    """Get file information and metadata"""
    try:
        from sqlalchemy import select

        # Get file information
        result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
        file_record = result.scalar_one_or_none()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        # Get worksheet information
        worksheets_result = await db.execute(
            select(WorksheetData).where(WorksheetData.file_id == file_id)
        )
        worksheets = worksheets_result.scalars().all()

        file_info = {
            "file_id": file_record.id,
            "filename": file_record.filename,
            "original_filename": file_record.original_filename,
            "file_size": file_record.file_size,
            "content_type": file_record.content_type,
            "status": file_record.status,
            "created_at": file_record.created_at.isoformat(),
            "processed_at": file_record.processed_at.isoformat() if file_record.processed_at else None,
            "metadata": file_record.meta_data,
            "worksheets": [
                {
                    "worksheet_id": ws.id,
                    "sheet_name": ws.sheet_name,
                    "sheet_index": ws.sheet_index,
                    "row_count": ws.row_count,
                    "column_count": ws.column_count,
                    "column_headers": ws.column_headers,
                    "data_types": ws.data_types
                }
                for ws in worksheets
            ]
        }

        return {
            "status": "success",
            "data": file_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve file info: {str(e)}")


@router.get("/files/{file_id}/worksheets/{worksheet_id}/data")
async def get_worksheet_data(
    file_id: str,
    worksheet_id: str,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get data from a specific worksheet"""
    try:
        from sqlalchemy import select

        # Verify worksheet belongs to file
        worksheet_result = await db.execute(
            select(WorksheetData).where(
                WorksheetData.id == worksheet_id,
                WorksheetData.file_id == file_id
            )
        )
        worksheet = worksheet_result.scalar_one_or_none()

        if not worksheet:
            raise HTTPException(status_code=404, detail="Worksheet not found")

        # Get rows with pagination
        rows_result = await db.execute(
            select(WorksheetRow)
            .where(WorksheetRow.worksheet_id == worksheet_id)
            .order_by(WorksheetRow.row_index)
            .offset(offset)
            .limit(limit)
        )
        rows = rows_result.scalars().all()

        return {
            "status": "success",
            "data": {
                "worksheet_info": {
                    "worksheet_id": worksheet.id,
                    "sheet_name": worksheet.sheet_name,
                    "row_count": worksheet.row_count,
                    "column_count": worksheet.column_count,
                    "column_headers": worksheet.column_headers,
                    "data_types": worksheet.data_types
                },
                "rows": [
                    {
                        "row_index": row.row_index,
                        "data": row.row_data
                    }
                    for row in rows
                ],
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "total_rows": worksheet.row_count,
                    "returned_rows": len(rows)
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve worksheet data: {str(e)}")


@router.post("/files/{file_id}/query")
async def query_file_data(
    file_id: str,
    query_request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Query file data with natural language or structured query"""
    try:
        from sqlalchemy import select

        # Verify file exists
        result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
        file_record = result.scalar_one_or_none()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        query_text = query_request.get("query", "")
        if not query_text:
            raise HTTPException(status_code=400, detail="Query text is required")

        # For now, return a simple response
        # In the future, this would process the natural language query
        # and execute appropriate database queries or use AI agents

        return {
            "status": "success",
            "query": query_text,
            "message": "Query processing will be implemented with AI agent integration",
            "file_id": file_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")