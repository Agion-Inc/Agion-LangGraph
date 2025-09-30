"""
Unified Storage Service for Agent-Chat
Seamlessly switches between local filesystem and Azure Blob Storage
"""

import os
from typing import Optional, Dict, Any, List, AsyncIterator, Union
from pathlib import Path
from abc import ABC, abstractmethod
import uuid
from datetime import datetime

from fastapi import UploadFile
from core.config import settings
from services.file_storage import FileStorageService
from services.azure_blob_storage import AzureBlobStorageService


class StorageInterface(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    async def store_file(
        self,
        upload_file: UploadFile,
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store a file and return file information"""
        pass
    
    @abstractmethod
    async def get_file(self, file_path: str) -> Optional[Union[Path, bytes]]:
        """Retrieve a file"""
        pass
    
    @abstractmethod
    async def get_file_stream(self, file_path: str) -> Optional[AsyncIterator[bytes]]:
        """Get file as stream for large files"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file"""
        pass
    
    @abstractmethod
    async def list_files(
        self,
        prefix: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List files with optional filtering"""
        pass
    
    @abstractmethod
    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a file"""
        pass
    
    @abstractmethod
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        pass


class LocalStorageAdapter(StorageInterface):
    """Adapter for local filesystem storage"""
    
    def __init__(self):
        self.storage = FileStorageService(settings.upload_dir)
    
    async def store_file(
        self,
        upload_file: UploadFile,
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store file locally"""
        result = await self.storage.store_file(upload_file, file_id, metadata)
        # Add URL-like fields for compatibility
        result['blob_name'] = result['file_path']
        result['blob_url'] = f"file://{result['absolute_path']}"
        result['sas_url'] = None  # Not applicable for local storage
        return result
    
    async def get_file(self, file_path: str) -> Optional[Path]:
        """Get local file path"""
        return await self.storage.get_file(file_path)
    
    async def get_file_stream(self, file_path: str) -> Optional[AsyncIterator[bytes]]:
        """Stream file from local storage"""
        file_path_obj = await self.get_file(file_path)
        if not file_path_obj:
            return None
        
        async def stream_generator():
            import aiofiles
            async with aiofiles.open(file_path_obj, 'rb') as f:
                chunk_size = 8192
                while chunk := await f.read(chunk_size):
                    yield chunk
        
        return stream_generator()
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete local file"""
        return await self.storage.delete_file(file_path)
    
    async def list_files(
        self,
        prefix: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List local files"""
        return await self.storage.list_files(category, limit, offset)
    
    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get local file information"""
        stats = await self.storage.get_file_stats(file_path)
        if not stats:
            return None
        
        # Format to match Azure response structure
        return {
            'name': file_path,
            'size': stats['size'],
            'content_type': None,  # Would need to determine from file
            'last_modified': stats['modified_at'],
            'etag': None,
            'metadata': {},
            'blob_url': f"file://{settings.upload_dir}/{file_path}"
        }
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get local storage statistics"""
        return await self.storage.get_storage_stats()


class AzureStorageAdapter(StorageInterface):
    """Adapter for Azure Blob Storage"""
    
    def __init__(self):
        self.storage = AzureBlobStorageService(
            settings.azure_storage_connection_string,
            settings.azure_storage_container_name
        )
    
    async def store_file(
        self,
        upload_file: UploadFile,
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store file in Azure Blob Storage"""
        result = await self.storage.upload_file(upload_file, file_id, metadata)
        # Add local path fields for compatibility
        result['file_path'] = result['blob_name']
        result['absolute_path'] = result['blob_url']
        return result
    
    async def get_file(self, file_path: str) -> Optional[bytes]:
        """Download file from Azure"""
        return await self.storage.download_file(file_path)
    
    async def get_file_stream(self, file_path: str) -> Optional[AsyncIterator[bytes]]:
        """Stream file from Azure"""
        return await self.storage.download_file_stream(file_path)
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from Azure"""
        return await self.storage.delete_file(file_path)
    
    async def list_files(
        self,
        prefix: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List files in Azure"""
        files = await self.storage.list_files(prefix, category)
        # Apply pagination
        return files[offset:offset + limit]
    
    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get Azure file information"""
        return await self.storage.get_file_info(file_path)
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get Azure storage statistics"""
        return await self.storage.get_storage_stats()
    
    async def generate_sas_url(
        self,
        file_path: str,
        expiry_days: Optional[int] = None,
        permission: str = 'r'
    ) -> str:
        """Generate SAS URL for direct access (Azure-specific feature)"""
        expiry = expiry_days or settings.azure_storage_sas_expiry_days
        return self.storage.generate_sas_url(file_path, expiry, permission)
    
    async def cleanup(self):
        """Cleanup Azure resources"""
        await self.storage.cleanup()


class UnifiedStorageService:
    """
    Unified storage service that automatically selects backend
    based on configuration
    """
    
    def __init__(self):
        self._adapter: Optional[StorageInterface] = None
        self._backend = settings.storage_backend.lower()
    
    @property
    def adapter(self) -> StorageInterface:
        """Get or create the storage adapter"""
        if not self._adapter:
            if self._backend == 'azure':
                if not settings.azure_storage_connection_string:
                    raise ValueError(
                        "Azure storage backend selected but AZURE_STORAGE_CONNECTION_STRING not configured"
                    )
                self._adapter = AzureStorageAdapter()
            else:
                self._adapter = LocalStorageAdapter()
        return self._adapter
    
    @property
    def is_azure(self) -> bool:
        """Check if using Azure storage"""
        return self._backend == 'azure'
    
    @property
    def is_local(self) -> bool:
        """Check if using local storage"""
        return self._backend == 'local'
    
    async def store_file(
        self,
        upload_file: UploadFile,
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store file using configured backend"""
        # Add storage backend to metadata
        if metadata is None:
            metadata = {}
        metadata['storage_backend'] = self._backend
        
        result = await self.adapter.store_file(upload_file, file_id, metadata)
        result['storage_backend'] = self._backend
        return result
    
    async def get_file(self, file_path: str) -> Optional[Union[Path, bytes]]:
        """Get file from configured backend"""
        return await self.adapter.get_file(file_path)
    
    async def get_file_stream(self, file_path: str) -> Optional[AsyncIterator[bytes]]:
        """Stream file from configured backend"""
        return await self.adapter.get_file_stream(file_path)
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from configured backend"""
        return await self.adapter.delete_file(file_path)
    
    async def list_files(
        self,
        prefix: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List files from configured backend"""
        return await self.adapter.list_files(prefix, category, limit, offset)
    
    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file information from configured backend"""
        info = await self.adapter.get_file_info(file_path)
        if info:
            info['storage_backend'] = self._backend
        return info
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics from configured backend"""
        stats = await self.adapter.get_storage_stats()
        stats['storage_backend'] = self._backend
        return stats
    
    async def generate_download_url(
        self,
        file_path: str,
        expiry_days: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate download URL for the file
        - For Azure: Returns SAS URL
        - For Local: Returns file:// URL or API endpoint
        """
        if self.is_azure and isinstance(self.adapter, AzureStorageAdapter):
            return await self.adapter.generate_sas_url(file_path, expiry_days, 'r')
        else:
            # For local storage, return a file URL or API endpoint
            file_obj = await self.adapter.get_file(file_path)
            if file_obj and isinstance(file_obj, Path):
                return f"file://{file_obj}"
            return None
    
    async def cleanup(self):
        """Cleanup resources if needed"""
        if self.is_azure and isinstance(self.adapter, AzureStorageAdapter):
            await self.adapter.cleanup()


# Global unified storage instance
unified_storage = UnifiedStorageService()
