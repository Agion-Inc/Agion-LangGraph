# Quick Start: File Upload System

## 🚀 Getting Started

### 1. Install Dependencies

```bash
cd /Users/mikko/Documents/Github/RG-Brands/Agent-Chat/backend

# Install Python dependencies
pip install aiofiles pandas openpyxl

# or using requirements
pip install -r requirements.txt
```

### 2. Create Storage Directories

```bash
# Create organized storage structure
mkdir -p uploads/{excel,csv,json,parquet,other}
mkdir -p processed temp archives thumbnails

# Set permissions
chmod 755 uploads processed temp archives thumbnails
```

### 3. Update Main Application

Add the new file routes to `main.py`:

```python
# Replace old files import
from api import files_v2 as files

# The router will automatically work with new endpoints
app.include_router(files.router, prefix=settings.api_prefix, tags=["files"])
```

### 4. Run Migration (if you have existing files)

```bash
# Backup database first!
cp bpchat.db bpchat.db.backup

# Run migration
python migrate_blob_to_filesystem.py
```

### 5. Start Backend

```bash
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Test File Upload

```bash
# Upload a single file
curl -X POST "http://localhost:8000/api/v1/files/upload" \
  -F "file=@sample.xlsx" \
  -F "process_immediately=true" \
  -F "upload_source=web_ui"

# Upload multiple files
curl -X POST "http://localhost:8000/api/v1/files/upload-multiple" \
  -F "files=@file1.xlsx" \
  -F "files=@file2.csv" \
  -F "process_immediately=true"

# List files
curl "http://localhost:8000/api/v1/files?page=1&size=20"

# Get file info
curl "http://localhost:8000/api/v1/files/{file_id}"

# Download file
curl "http://localhost:8000/api/v1/files/{file_id}/download" -o downloaded.xlsx

# Delete file
curl -X DELETE "http://localhost:8000/api/v1/files/{file_id}"

# Get storage stats
curl "http://localhost:8000/api/v1/files/storage/stats"
```

## 🎨 Frontend Setup

### 1. Add File Manager Route

Update `frontend/src/App.tsx`:

```typescript
import FileManagerPage from './pages/FileManagerPage'

// Add route
<Route path="/files" element={<FileManagerPage />} />
```

### 2. Add Navigation Link

```typescript
<Link to="/files">
  <DocumentIcon className="w-5 h-5" />
  <span>Files</span>
</Link>
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm start
```

Visit: http://localhost:3000/files

## 📊 Features

### File Storage Service
- ✅ Organized directory structure by date and category
- ✅ Streaming file operations (memory efficient)
- ✅ File deduplication using SHA-256 hashing
- ✅ Automatic cleanup of temp files
- ✅ Archive management
- ✅ Security with path validation

### API Endpoints
- ✅ Single file upload with immediate processing
- ✅ Multiple file upload (batch)
- ✅ List files with filtering and pagination
- ✅ Search files by name
- ✅ Filter by category and status
- ✅ Download files with streaming
- ✅ Delete files (cascade deletion)
- ✅ Storage statistics dashboard

### File Management UI
- ✅ Drag-and-drop file upload
- ✅ Advanced search and filters
- ✅ File preview and data viewing
- ✅ Download and delete operations
- ✅ Storage statistics visualization
- ✅ Pagination support
- ✅ Real-time upload progress
- ✅ Error handling with retries

## 🔧 Configuration

### Environment Variables (.env)

```bash
# File Storage
UPLOAD_DIR=uploads
MAX_FILE_SIZE=104857600  # 100MB in bytes
ALLOWED_FILE_TYPES=.xlsx,.xls,.csv,.json,.parquet

# Database
DATABASE_URL=sqlite+aiosqlite:///./bpchat.db

# API
API_PREFIX=/api/v1
```

### Storage Limits

```python
# In core/config.py
max_file_size: int = 100 * 1024 * 1024  # 100MB
allowed_file_types: List[str] = [".xlsx", ".csv", ".json", ".parquet"]
```

## 🐛 Troubleshooting

### Issue: Permission Denied

```bash
# Fix permissions
chmod -R 755 uploads
chown -R $USER:$USER uploads
```

### Issue: Database locked

```bash
# SQLite limitation - use PostgreSQL for production
# Or ensure only one process accesses database
```

### Issue: File not found after upload

```bash
# Check storage directory exists
ls -la uploads/

# Check file record in database
sqlite3 bpchat.db "SELECT id, filename, file_path FROM uploaded_files LIMIT 10;"

# Verify file on disk
find uploads -type f -name "*.xlsx"
```

### Issue: Upload fails with large files

```bash
# Increase Nginx timeout (if using Nginx)
client_max_body_size 100M;
client_body_timeout 300s;

# Increase uvicorn timeout
uvicorn main:app --timeout-keep-alive 300
```

## 📈 Performance Tips

1. **Use streaming for large files** - Already implemented in storage service
2. **Enable file deduplication** - Automatically checks SHA-256 hash
3. **Clean up temp files regularly** - Run cleanup task daily
4. **Index database columns** - Add indexes on frequently queried columns
5. **Use CDN for file downloads** - For production deployments

```sql
-- Optimize database
CREATE INDEX idx_uploaded_files_category ON uploaded_files(category);
CREATE INDEX idx_uploaded_files_status ON uploaded_files(status);
CREATE INDEX idx_uploaded_files_created_at ON uploaded_files(created_at);
```

## 🔒 Security

1. **File type validation** - Only allowed types accepted
2. **File size limits** - Enforced at API level
3. **Path traversal prevention** - All paths validated
4. **Access logging** - Complete audit trail
5. **Content scanning** - Can integrate virus scanning

```python
# Add virus scanning (optional)
async def scan_file(file_path: Path) -> bool:
    # Integrate ClamAV or similar
    pass
```

## 📚 API Documentation

Visit: http://localhost:8000/docs

Interactive API documentation with:
- All endpoints documented
- Try-it-out functionality
- Request/response schemas
- Authentication examples

## 🚢 Deployment

### Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Create storage directories
RUN mkdir -p uploads processed temp archives thumbnails

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
services:
  backend:
    build: ./backend
    volumes:
      - ./uploads:/app/uploads
      - ./data:/app/data
    environment:
      - UPLOAD_DIR=/app/uploads
      - DATABASE_URL=sqlite+aiosqlite:///./data/bpchat.db
    ports:
      - "8000:8000"
```

## 📞 Support

For issues or questions:
- Check logs: `tail -f logs/app.log`
- Review documentation: `/docs`
- Create issue: GitHub Issues

## ✅ Checklist

- [ ] Dependencies installed
- [ ] Storage directories created
- [ ] Database migrated (if needed)
- [ ] Backend running
- [ ] Frontend updated
- [ ] Test file upload works
- [ ] Test file download works
- [ ] Test file deletion works
- [ ] Storage stats displaying
- [ ] File management UI accessible

---

**Next Steps:**
1. Test all features thoroughly
2. Review security settings
3. Set up monitoring
4. Deploy to staging
5. Run load tests
6. Deploy to production
