"""
Agent-Chat File Storage Service
Elegant file storage with organized directory structure and streaming support
"""

import os
import shutil
import hashlib
import asyncio
from typing import Optional, Dict, Any, List, BinaryIO
from pathlib import Path
from datetime import datetime
import aiofiles
from fastapi import UploadFile
import uuid

from core.config import settings


class FileStorageService:
    """
    Elegant file storage service with:
    - Organized directory structure by date and type
    - Streaming file operations for memory efficiency
    - File deduplication using content hashing
    - Automatic cleanup and archival
    - Secure file access with validation
    """

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.upload_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create organized directory structure
        self._ensure_directory_structure()

    def _ensure_directory_structure(self):
        """Create organized directory structure"""
        directories = [
            "uploads/excel",      # Excel files (.xlsx, .xls)
            "uploads/csv",        # CSV files
            "uploads/json",       # JSON files
            "uploads/parquet",    # Parquet files
            "uploads/other",      # Other supported formats
            "processed",          # Processed/converted files
            "temp",              # Temporary files during processing
            "archives",          # Archived files
            "thumbnails",        # File previews/thumbnails
        ]
        
        for directory in directories:
            (self.base_path / directory).mkdir(parents=True, exist_ok=True)

    def _get_file_category(self, filename: str) -> str:
        """Determine file category based on extension"""
        extension = Path(filename).suffix.lower()
        
        category_map = {
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.csv': 'csv',
            '.json': 'json',
            '.parquet': 'parquet',
        }
        
        return category_map.get(extension, 'other')

    def _generate_file_path(self, filename: str, file_id: str) -> Path:
        """Generate organized file path with date-based structure"""
        category = self._get_file_category(filename)
        today = datetime.now()
        
        # Create date-based subdirectory: uploads/excel/2025/01/28/
        date_path = today.strftime("%Y/%m/%d")
        
        # Use file ID as filename to avoid conflicts, keep original extension
        extension = Path(filename).suffix
        safe_filename = f"{file_id}{extension}"
        
        return self.base_path / "uploads" / category / date_path / safe_filename

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file for deduplication"""
        hash_sha256 = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            # Read in chunks to handle large files efficiently
            while chunk := await f.read(8192):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()

    async def store_file(
        self, 
        upload_file: UploadFile, 
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store uploaded file with streaming for memory efficiency
        
        Returns:
            Dict containing file information and storage details
        """
        try:
            # Generate organized file path
            file_path = self._generate_file_path(upload_file.filename, file_id)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Stream file to disk to handle large files efficiently
            async with aiofiles.open(file_path, 'wb') as dest_file:
                # Reset file pointer
                await upload_file.seek(0)
                
                # Stream in chunks
                while chunk := await upload_file.read(8192):
                    await dest_file.write(chunk)
            
            # Calculate file hash for deduplication
            file_hash = await self._calculate_file_hash(file_path)
            
            # Get file stats
            file_stats = file_path.stat()
            
            # Create file info
            file_info = {
                "file_id": file_id,
                "filename": upload_file.filename,
                "file_path": str(file_path.relative_to(self.base_path)),
                "absolute_path": str(file_path),
                "file_size": file_stats.st_size,
                "content_type": upload_file.content_type,
                "file_hash": file_hash,
                "category": self._get_file_category(upload_file.filename),
                "stored_at": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                "metadata": metadata or {}
            }
            
            return file_info
            
        except Exception as e:
            # Clean up partial file if error occurs
            if file_path.exists():
                file_path.unlink()
            raise Exception(f"Failed to store file: {str(e)}")

    async def get_file(self, file_path: str) -> Optional[Path]:
        """Get file path if it exists and is valid"""
        try:
            full_path = self.base_path / file_path
            
            # Security check: ensure file is within base directory
            if not str(full_path.resolve()).startswith(str(self.base_path.resolve())):
                raise ValueError("Invalid file path - security violation")
            
            if full_path.exists() and full_path.is_file():
                return full_path
            
            return None
            
        except Exception:
            return None

    async def delete_file(self, file_path: str) -> bool:
        """Delete file and clean up empty directories"""
        try:
            full_path = self.base_path / file_path
            
            # Security check
            if not str(full_path.resolve()).startswith(str(self.base_path.resolve())):
                return False
            
            if full_path.exists():
                full_path.unlink()
                
                # Clean up empty parent directories
                parent = full_path.parent
                while parent != self.base_path and parent.exists():
                    try:
                        parent.rmdir()  # Only removes if empty
                        parent = parent.parent
                    except OSError:
                        break  # Directory not empty
                
                return True
            
            return False
            
        except Exception:
            return False

    async def move_to_archive(self, file_path: str) -> Optional[str]:
        """Move file to archive directory"""
        try:
            source_path = self.base_path / file_path
            
            if not source_path.exists():
                return None
            
            # Create archive path with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"{timestamp}_{source_path.name}"
            archive_path = self.base_path / "archives" / archive_filename
            
            # Ensure archive directory exists
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(str(source_path), str(archive_path))
            
            return str(archive_path.relative_to(self.base_path))
            
        except Exception:
            return None

    async def get_file_stats(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get detailed file statistics"""
        try:
            full_path = self.base_path / file_path
            
            if not full_path.exists():
                return None
            
            stats = full_path.stat()
            
            return {
                "size": stats.st_size,
                "created_at": datetime.fromtimestamp(stats.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "accessed_at": datetime.fromtimestamp(stats.st_atime).isoformat(),
                "is_file": full_path.is_file(),
                "is_readable": os.access(full_path, os.R_OK),
                "is_writable": os.access(full_path, os.W_OK),
            }
            
        except Exception:
            return None

    async def list_files(
        self, 
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List files with optional filtering"""
        try:
            files = []
            
            # Determine search path
            if category:
                search_path = self.base_path / "uploads" / category
            else:
                search_path = self.base_path / "uploads"
            
            # Recursively find all files
            if search_path.exists():
                for file_path in search_path.rglob("*"):
                    if file_path.is_file():
                        stats = file_path.stat()
                        
                        files.append({
                            "relative_path": str(file_path.relative_to(self.base_path)),
                            "filename": file_path.name,
                            "size": stats.st_size,
                            "category": self._get_file_category(file_path.name),
                            "created_at": datetime.fromtimestamp(stats.st_ctime).isoformat(),
                            "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                        })
            
            # Sort by creation time (newest first)
            files.sort(key=lambda x: x["created_at"], reverse=True)
            
            # Apply pagination
            return files[offset:offset + limit]
            
        except Exception:
            return []

    async def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up temporary files older than specified hours"""
        try:
            temp_dir = self.base_path / "temp"
            
            if not temp_dir.exists():
                return
            
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
            
            for file_path in temp_dir.rglob("*"):
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
            
            # Clean up empty directories
            for dir_path in temp_dir.rglob("*"):
                if dir_path.is_dir():
                    try:
                        dir_path.rmdir()
                    except OSError:
                        pass  # Directory not empty
                        
        except Exception:
            pass  # Silent cleanup failure

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            stats = {
                "total_files": 0,
                "total_size": 0,
                "categories": {},
                "storage_path": str(self.base_path),
            }
            
            uploads_dir = self.base_path / "uploads"
            
            if uploads_dir.exists():
                for file_path in uploads_dir.rglob("*"):
                    if file_path.is_file():
                        file_size = file_path.stat().st_size
                        category = self._get_file_category(file_path.name)
                        
                        stats["total_files"] += 1
                        stats["total_size"] += file_size
                        
                        if category not in stats["categories"]:
                            stats["categories"][category] = {
                                "count": 0,
                                "size": 0
                            }
                        
                        stats["categories"][category]["count"] += 1
                        stats["categories"][category]["size"] += file_size
            
            return stats
            
        except Exception:
            return {
                "total_files": 0,
                "total_size": 0,
                "categories": {},
                "storage_path": str(self.base_path),
                "error": "Failed to calculate storage stats"
            }


# Global storage service instance
storage_service = FileStorageService()
