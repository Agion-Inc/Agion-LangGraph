# Azure Blob Storage Setup Guide

## Overview

Agent-Chat supports both local file storage and Azure Blob Storage for managing uploaded files. This guide explains how to configure and use Azure Blob Storage as your file storage backend.

## Benefits of Azure Blob Storage

- **Scalability**: Virtually unlimited storage capacity
- **Durability**: 99.999999999% (11 9's) durability
- **Global Access**: Files accessible from anywhere via SAS URLs
- **Cost-Effective**: Pay only for what you use
- **Security**: Enterprise-grade security and encryption
- **Performance**: High-throughput for concurrent operations

## Prerequisites

1. An Azure account with an active subscription
2. Azure Storage Account created
3. Storage Account connection string

## Azure Storage Account Setup

### 1. Create Storage Account

1. Log in to [Azure Portal](https://portal.azure.com)
2. Click "Create a resource" > "Storage" > "Storage account"
3. Configure the storage account:
   - **Resource group**: Create new or use existing
   - **Storage account name**: Choose a unique name (e.g., `bpchatstorage`)
   - **Region**: Select nearest to your users
   - **Performance**: Standard (recommended for files)
   - **Redundancy**: LRS or GRS based on needs

### 2. Get Connection String

1. Navigate to your Storage Account
2. Go to "Access keys" under "Security + networking"
3. Copy the "Connection string" from key1 or key2

## Application Configuration

### 1. Environment Variables

Add these to your `.env` file:

```bash
# Storage Backend Configuration
STORAGE_BACKEND=azure  # Change from 'local' to 'azure'

# Azure Storage Configuration
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=your_account;AccountKey=your_key;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER_NAME=bpchat-files  # Optional, defaults to 'bpchat-files'
AZURE_STORAGE_SAS_EXPIRY_DAYS=7  # Optional, defaults to 7 days
```

### 2. Install Dependencies

The Azure storage dependencies are already included in requirements.txt:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install azure-storage-blob azure-core
```

## Storage Backends Comparison

| Feature | Local Storage | Azure Blob Storage |
|---------|--------------|-------------------|
| Setup Complexity | Simple | Moderate |
| Scalability | Limited by disk | Unlimited |
| Cost | Server storage cost | Pay-per-use |
| Access Speed | Fast (local) | Fast (with CDN) |
| Global Access | Requires VPN/tunnel | Direct URLs |
| Backup | Manual | Automatic options |
| File Sharing | API only | SAS URLs |
| Max File Size | Disk limited | 5 TB per blob |

## File Organization Structure

Both storage backends use the same organizational structure:

```
category/
  └── year/
      └── month/
          └── day/
              └── file_id/
                  └── original_filename.ext
```

Example:
```
excel/2025/01/28/550e8400-e29b-41d4-a716-446655440000/sales_data.xlsx
```

## API Endpoints

The API endpoints work seamlessly with both storage backends:

### Upload File
```bash
POST /api/v1/files/upload
Content-Type: multipart/form-data

file: [file]
process_immediately: true
upload_source: web_ui
```

### Download File
```bash
GET /api/v1/files/{file_id}/download
```

### Get Download URL (Direct Access)
```bash
GET /api/v1/files/{file_id}/download-url?expiry_days=7
```

Response for Azure:
```json
{
  "download_url": "https://account.blob.core.windows.net/container/path?sv=...",
  "expires_in_days": 7,
  "storage_backend": "azure"
}
```

### List Files
```bash
GET /api/v1/files?page=1&size=20&category=excel
```

### Storage Statistics
```bash
GET /api/v1/files/storage/stats
```

## Testing Your Configuration

### 1. Run Test Script

```bash
python test_azure_storage.py
```

This will test:
- File upload
- File download
- File info retrieval
- SAS URL generation
- File listing
- Storage statistics
- File deletion

### 2. Manual Testing

```bash
# Check current configuration
python -c "from core.config import settings; print(f'Storage: {settings.storage_backend}')"

# Test upload via API
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@test.xlsx" \
  -F "process_immediately=true"
```

## Security Best Practices

### 1. Connection String Security
- **Never** commit connection strings to version control
- Use environment variables or Azure Key Vault
- Rotate storage keys regularly
- Use managed identities in production (Azure VMs)

### 2. Container Access
- Keep containers private (no anonymous access)
- Use SAS tokens for temporary access
- Set appropriate expiry times for SAS tokens
- Monitor access logs

### 3. Network Security
- Enable firewall rules on Storage Account
- Use Private Endpoints for VNet integration
- Enable HTTPS-only access
- Configure CORS if needed

## Cost Optimization

### 1. Storage Tiers
- **Hot**: Frequently accessed files (default)
- **Cool**: Infrequently accessed (30+ days)
- **Archive**: Rarely accessed (180+ days)

### 2. Lifecycle Management
Set up policies to:
- Move old files to cooler tiers
- Delete temporary files
- Archive processed files

### 3. Monitoring
- Set up cost alerts
- Monitor storage metrics
- Review access patterns

## Troubleshooting

### Common Issues

#### 1. Connection String Invalid
```
Error: Invalid connection string
```
**Solution**: Verify connection string format and credentials

#### 2. Container Not Found
```
Error: Container 'bpchat-files' not found
```
**Solution**: Container is auto-created on first upload, or create manually in Azure Portal

#### 3. Access Denied
```
Error: 403 Forbidden
```
**Solution**: Check storage account keys and firewall settings

#### 4. Slow Uploads
**Solutions**:
- Check network connectivity
- Use nearest Azure region
- Consider Azure CDN for global access
- Implement chunked uploads for large files

### Debug Mode

Enable debug logging:
```python
# In your code
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Migration Guide

### From Local to Azure

1. **Export existing files**: Use the migration script to upload local files to Azure
2. **Update configuration**: Change `STORAGE_BACKEND=azure` in .env
3. **Test thoroughly**: Run test script to verify
4. **Monitor**: Check logs and metrics after deployment

### From Azure to Local

1. **Download files**: Use Azure Storage Explorer or AzCopy
2. **Update configuration**: Change `STORAGE_BACKEND=local`
3. **Verify file paths**: Ensure upload directory exists and has permissions

## Performance Tips

1. **Use Async Operations**: All storage operations are async for better performance
2. **Stream Large Files**: Files are streamed to avoid memory issues
3. **Enable CDN**: For global users, enable Azure CDN
4. **Batch Operations**: Use bulk upload endpoints for multiple files
5. **Connection Pooling**: Reuse blob clients (handled automatically)

## Monitoring and Logging

### Azure Portal Metrics
- Storage account metrics
- Blob storage insights
- Transaction logs
- Performance metrics

### Application Logging
All file operations are logged with:
- Operation type (upload, download, delete)
- File ID and metadata
- User information
- Timestamps
- Success/failure status

## Support and Resources

- [Azure Blob Storage Documentation](https://docs.microsoft.com/azure/storage/blobs/)
- [Python SDK Documentation](https://docs.microsoft.com/python/api/azure-storage-blob/)
- [Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)
- [Storage Explorer Tool](https://azure.microsoft.com/features/storage-explorer/)

## Conclusion

Azure Blob Storage provides a robust, scalable solution for file storage in Agent-Chat. The unified storage interface ensures seamless switching between local and cloud storage based on your needs.
