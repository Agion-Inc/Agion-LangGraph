"""
Azure Blob Storage Service for Agent-Chat
Efficient cloud-based file storage with directory-like organization
"""

import os
import io
import hashlib
import asyncio
from typing import Optional, Dict, Any, List, BinaryIO, AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path
import uuid

from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from azure.storage.blob import BlobSasPermissions, generate_blob_sas, ContentSettings
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
import aiofiles
from fastapi import UploadFile

from core.config import settings


class AzureBlobStorageService:
    """
    Azure Blob Storage service with:
    - Directory-like organization using blob prefixes
    - Streaming uploads/downloads for memory efficiency
    - SAS token generation for secure direct access
    - Automatic content type detection
    - Cost-optimized storage tiers
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        container_name: str = "bpchat-files"
    ):
        """Initialize Azure Blob Storage service"""
        self.connection_string = connection_string or settings.azure_storage_connection_string
        self.container_name = container_name
        self.account_name = self._extract_account_name(self.connection_string)
        self.account_key = self._extract_account_key(self.connection_string)
        
        # Initialize async clients
        self.blob_service_client: Optional[BlobServiceClient] = None
        self.container_client: Optional[ContainerClient] = None
        
    def _extract_account_name(self, connection_string: str) -> str:
        """Extract account name from connection string"""
        for part in connection_string.split(';'):
            if part.startswith('AccountName='):
                return part.split('=', 1)[1]
        return ""
    
    def _extract_account_key(self, connection_string: str) -> str:
        """Extract account key from connection string"""
        for part in connection_string.split(';'):
            if part.startswith('AccountKey='):
                # Account key might contain '=' so join everything after first '='
                return part.split('=', 1)[1]
        return ""
    
    async def _ensure_initialized(self):
        """Ensure clients are initialized"""
        if not self.blob_service_client:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            
            # Create container if it doesn't exist
            try:
                await self.container_client.create_container()
            except ResourceExistsError:
                pass  # Container already exists
    
    def _generate_blob_path(self, file_id: str, filename: str, category: str = None) -> str:
        """
        Generate organized blob path
        Structure: category/year/month/day/file_id/filename
        """
        today = datetime.utcnow()
        date_path = today.strftime("%Y/%m/%d")
        
        if not category:
            extension = Path(filename).suffix.lower()
            category_map = {
                '.xlsx': 'excel',
                '.xls': 'excel',
                '.csv': 'csv',
                '.json': 'json',
                '.parquet': 'parquet',
                '.pdf': 'pdf',
                '.jpg': 'images',
                '.jpeg': 'images',
                '.png': 'images',
            }
            category = category_map.get(extension, 'other')
        
        return f"{category}/{date_path}/{file_id}/{filename}"
    
    async def upload_file(
        self,
        file: UploadFile,
        file_id: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload file to Azure Blob Storage
        Returns blob URL and metadata
        """
        await self._ensure_initialized()
        
        # Generate blob path
        blob_name = self._generate_blob_path(file_id, file.filename)
        blob_client = self.container_client.get_blob_client(blob_name)
        
        # Prepare metadata - Azure requires all metadata values to be strings
        blob_metadata = {
            'original_filename': str(file.filename) if file.filename else '',
            'file_id': str(file_id),
            'upload_timestamp': datetime.utcnow().isoformat(),
            'content_type': str(file.content_type or 'application/octet-stream')
        }
        if metadata:
            # Convert all metadata values to strings
            for key, value in metadata.items():
                blob_metadata[key] = str(value) if value is not None else ''
        
        # Stream upload to blob
        file_size = 0
        file_hash = hashlib.sha256()
        
        # Read file in chunks and upload
        file_content = await file.read()
        file_size = len(file_content)
        file_hash.update(file_content)
        
        await blob_client.upload_blob(
            data=file_content,
            metadata=blob_metadata,
            content_settings=ContentSettings(content_type=file.content_type or 'application/octet-stream'),
            overwrite=True
        )
        
        # Generate SAS URL for direct access (valid for 7 days)
        sas_url = self.generate_sas_url(blob_name, expiry_days=7, permission='r')
        
        return {
            'blob_name': blob_name,
            'blob_url': f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}",
            'sas_url': sas_url,
            'file_size': file_size,
            'file_hash': file_hash.hexdigest(),
            'category': blob_name.split('/')[0],
            'metadata': blob_metadata
        }
    
    async def download_file(self, blob_name: str) -> bytes:
        """Download file from blob storage"""
        await self._ensure_initialized()
        
        blob_client = self.container_client.get_blob_client(blob_name)
        
        try:
            stream = await blob_client.download_blob()
            data = await stream.readall()
            return data
        except ResourceNotFoundError:
            return None
    
    async def download_file_stream(self, blob_name: str) -> AsyncIterator[bytes]:
        """Download file as async stream for large files"""
        await self._ensure_initialized()
        
        blob_client = self.container_client.get_blob_client(blob_name)
        
        try:
            stream = await blob_client.download_blob()
            async for chunk in stream.chunks():
                yield chunk
        except ResourceNotFoundError:
            return
    
    async def delete_file(self, blob_name: str) -> bool:
        """Delete file from blob storage"""
        await self._ensure_initialized()
        
        blob_client = self.container_client.get_blob_client(blob_name)
        
        try:
            await blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            return False
    
    async def list_files(
        self,
        prefix: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List files in blob storage"""
        await self._ensure_initialized()
        
        # Build prefix for filtering
        if category:
            prefix = f"{category}/"
        elif prefix and not prefix.endswith('/'):
            prefix = f"{prefix}/"
        
        files = []
        async for blob in self.container_client.list_blobs(name_starts_with=prefix):
            files.append({
                'name': blob.name,
                'size': blob.size,
                'last_modified': blob.last_modified,
                'content_type': blob.content_settings.content_type if blob.content_settings else None,
                'metadata': blob.metadata
            })
        
        return files
    
    async def get_file_info(self, blob_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a file"""
        await self._ensure_initialized()
        
        blob_client = self.container_client.get_blob_client(blob_name)
        
        try:
            properties = await blob_client.get_blob_properties()
            return {
                'name': properties.name,
                'size': properties.size,
                'content_type': properties.content_settings.content_type if properties.content_settings else None,
                'last_modified': properties.last_modified,
                'etag': properties.etag,
                'metadata': properties.metadata,
                'blob_url': f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}"
            }
        except ResourceNotFoundError:
            return None
    
    def generate_sas_url(
        self,
        blob_name: str,
        expiry_days: int = 1,
        permission: str = 'r'
    ) -> str:
        """
        Generate SAS URL for direct blob access
        permission: 'r' (read), 'w' (write), 'rw' (read/write)
        """
        # Set permissions
        permissions = BlobSasPermissions()
        if 'r' in permission:
            permissions.read = True
        if 'w' in permission:
            permissions.write = True
            permissions.create = True
        
        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=self.account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self.account_key,
            permission=permissions,
            expiry=datetime.utcnow() + timedelta(days=expiry_days)
        )
        
        # Construct full URL
        return f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
    
    async def move_file(self, source_blob: str, dest_blob: str) -> bool:
        """Move file within blob storage"""
        await self._ensure_initialized()
        
        source_client = self.container_client.get_blob_client(source_blob)
        dest_client = self.container_client.get_blob_client(dest_blob)
        
        try:
            # Copy to new location
            await dest_client.start_copy_from_url(
                f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{source_blob}"
            )
            
            # Delete original
            await source_client.delete_blob()
            return True
        except Exception:
            return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        await self._ensure_initialized()
        
        total_size = 0
        total_count = 0
        categories = {}
        
        async for blob in self.container_client.list_blobs():
            total_size += blob.size
            total_count += 1
            
            # Extract category from path
            category = blob.name.split('/')[0] if '/' in blob.name else 'root'
            if category not in categories:
                categories[category] = {'count': 0, 'size': 0}
            categories[category]['count'] += 1
            categories[category]['size'] += blob.size
        
        return {
            'total_files': total_count,
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_size_gb': round(total_size / (1024 * 1024 * 1024), 3),
            'categories': categories,
            'storage_account': self.account_name,
            'container': self.container_name
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.blob_service_client:
            await self.blob_service_client.close()
            self.blob_service_client = None
            self.container_client = None


# Global instance
azure_blob_storage = AzureBlobStorageService()
