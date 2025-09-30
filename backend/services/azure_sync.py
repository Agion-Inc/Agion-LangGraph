"""
Azure Blob Storage to Database Synchronization Service
Ensures file metadata consistency between Azure and local database
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from core.database import get_db
from models import UploadedFile
from services.azure_blob_storage import AzureBlobStorageService
from core.config import settings

logger = logging.getLogger(__name__)


class AzureSyncService:
    """
    Service to synchronize file metadata between Azure Blob Storage and local database.
    This ensures files uploaded through one session are visible in all sessions.
    """

    def __init__(self):
        self.azure_service = AzureBlobStorageService(
            settings.azure_storage_connection_string,
            settings.azure_storage_container_name
        )
        self.sync_interval = 300  # Sync every 5 minutes
        self._sync_task = None

    async def sync_azure_to_database(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Sync all files from Azure Blob Storage to the database.
        This will:
        1. List all files in Azure
        2. Check which ones are missing from the database
        3. Add missing files to the database
        4. Update metadata for existing files if needed
        """
        try:
            logger.info("Starting Azure to database synchronization...")
            
            # Get all files from Azure
            azure_files = await self.azure_service.list_files()
            logger.info(f"Found {len(azure_files)} files in Azure Blob Storage")

            # Get all file paths from database
            db_result = await db.execute(select(UploadedFile.file_path, UploadedFile.id))
            db_files_map = {row[0]: row[1] for row in db_result.fetchall()}
            
            added_count = 0
            updated_count = 0
            errors = []

            for azure_file in azure_files:
                try:
                    blob_name = azure_file['name']
                    
                    # Skip if not a valid file (could be a directory marker)
                    if not blob_name or blob_name.endswith('/'):
                        continue
                    
                    # Extract file information from blob metadata and path
                    metadata = azure_file.get('metadata', {})
                    file_id = metadata.get('file_id', None)
                    original_filename = metadata.get('original_filename', None)
                    
                    # If no metadata, try to extract from path structure
                    # Path format: category/year/month/day/file_id/filename
                    path_parts = blob_name.split('/')
                    if len(path_parts) >= 6:
                        category = path_parts[0]
                        potential_file_id = path_parts[4]
                        filename = path_parts[5]
                        
                        if not file_id:
                            file_id = potential_file_id
                        if not original_filename:
                            original_filename = filename
                    else:
                        # Fallback for files with non-standard paths
                        filename = Path(blob_name).name
                        if not original_filename:
                            original_filename = filename
                        if not file_id:
                            # Generate a file_id from the blob name (deterministic)
                            import hashlib
                            file_id = hashlib.md5(blob_name.encode()).hexdigest()
                        category = 'unknown'

                    # Check if file exists in database
                    if blob_name in db_files_map:
                        # File exists, check if we need to update metadata
                        existing_file = await db.execute(
                            select(UploadedFile).where(UploadedFile.file_path == blob_name)
                        )
                        existing_file = existing_file.scalar_one_or_none()
                        
                        if existing_file and existing_file.file_size != azure_file['size']:
                            # Update file size if different
                            existing_file.file_size = azure_file['size']
                            existing_file.last_accessed = datetime.utcnow()
                            updated_count += 1
                    else:
                        # File doesn't exist in database, add it
                        content_type = azure_file.get('content_type', 'application/octet-stream')
                        if not content_type and original_filename:
                            # Guess content type from filename
                            import mimetypes
                            content_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
                        
                        new_file = UploadedFile(
                            id=file_id,
                            filename=original_filename or filename,
                            original_filename=original_filename or filename,
                            file_size=azure_file['size'],
                            content_type=content_type,
                            file_path=blob_name,
                            file_hash=metadata.get('file_hash', ''),
                            category=category,
                            status='uploaded',  # Mark as uploaded since it's already in Azure
                            upload_source=metadata.get('upload_source', 'azure_sync'),
                            meta_data={
                                **metadata,
                                'synced_from_azure': True,
                                'sync_timestamp': datetime.utcnow().isoformat(),
                                'azure_last_modified': azure_file['last_modified'].isoformat() if azure_file.get('last_modified') else None
                            },
                            created_at=azure_file.get('last_modified', datetime.utcnow())
                        )
                        
                        db.add(new_file)
                        added_count += 1
                        logger.info(f"Added file from Azure: {blob_name}")

                except Exception as e:
                    error_msg = f"Error syncing file {azure_file.get('name', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Commit all changes
            await db.commit()
            
            result = {
                'status': 'success',
                'azure_files_count': len(azure_files),
                'db_files_count': len(db_files_map),
                'added': added_count,
                'updated': updated_count,
                'errors': errors,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Azure sync completed: {added_count} added, {updated_count} updated")
            return result

        except Exception as e:
            logger.error(f"Azure sync failed: {str(e)}")
            await db.rollback()
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def sync_database_to_azure(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Sync database entries to Azure (mainly for cleanup).
        This removes database entries for files that no longer exist in Azure.
        """
        try:
            logger.info("Starting database to Azure synchronization...")
            
            # Get all files from Azure
            azure_files = await self.azure_service.list_files()
            azure_blob_names = {f['name'] for f in azure_files if f.get('name')}
            
            # Get all files from database
            db_result = await db.execute(select(UploadedFile))
            db_files = db_result.scalars().all()
            
            removed_count = 0
            errors = []

            for db_file in db_files:
                try:
                    if db_file.file_path not in azure_blob_names:
                        # File exists in database but not in Azure, remove it
                        logger.warning(f"Removing orphaned database entry: {db_file.file_path}")
                        await db.delete(db_file)
                        removed_count += 1
                except Exception as e:
                    error_msg = f"Error removing orphaned entry {db_file.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            await db.commit()
            
            result = {
                'status': 'success',
                'db_files_checked': len(db_files),
                'removed': removed_count,
                'errors': errors,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Database cleanup completed: {removed_count} orphaned entries removed")
            return result

        except Exception as e:
            logger.error(f"Database cleanup failed: {str(e)}")
            await db.rollback()
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def full_sync(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Perform a full bidirectional sync:
        1. Sync Azure to database (add missing files)
        2. Sync database to Azure (remove orphaned entries)
        """
        logger.info("Starting full bidirectional sync...")
        
        # First sync from Azure to database
        azure_to_db_result = await self.sync_azure_to_database(db)
        
        # Then cleanup orphaned database entries
        db_to_azure_result = await self.sync_database_to_azure(db)
        
        return {
            'status': 'success' if azure_to_db_result['status'] == 'success' else 'partial',
            'azure_to_db': azure_to_db_result,
            'db_to_azure': db_to_azure_result,
            'timestamp': datetime.utcnow().isoformat()
        }

    async def start_background_sync(self):
        """Start background synchronization task"""
        if self._sync_task is None:
            self._sync_task = asyncio.create_task(self._background_sync_loop())
            logger.info(f"Started background Azure sync (interval: {self.sync_interval}s)")

    async def stop_background_sync(self):
        """Stop background synchronization task"""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            self._sync_task = None
            logger.info("Stopped background Azure sync")

    async def _background_sync_loop(self):
        """Background loop for periodic synchronization"""
        while True:
            try:
                await asyncio.sleep(self.sync_interval)
                
                # Get a database session for sync
                async for db in get_db():
                    try:
                        result = await self.full_sync(db)
                        if result['status'] != 'success':
                            logger.warning(f"Background sync completed with issues: {result}")
                    except Exception as e:
                        logger.error(f"Background sync error: {str(e)}")
                    finally:
                        break  # Exit the async for loop
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in background sync loop: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying


# Global sync service instance
azure_sync_service = AzureSyncService()
