# Backend Scripts

## Remove Duplicate Files

Script to find and remove duplicate files from storage based on file hash.

### Usage

```bash
# Dry run - preview what would be deleted (safe)
python scripts/remove_duplicate_files.py

# Actually delete duplicate files
python scripts/remove_duplicate_files.py --execute
```

### How it works

1. Scans all files in the database
2. Groups files by their SHA-256 hash
3. For each group of duplicates:
   - Keeps the oldest file (by upload date)
   - Marks newer duplicates for deletion
4. Shows summary of space that will be saved
5. Deletes duplicate files from both storage and database (only with --execute flag)

### Safety Features

- **Dry run by default**: Without `--execute`, no files are deleted
- **5-second countdown**: When using `--execute`, gives you time to cancel (Ctrl+C)
- **Keeps oldest file**: Preserves the first uploaded version
- **Detailed output**: Shows exactly what will be/was deleted

### Example Output

```
================================================================================
🧹 Duplicate File Cleanup Tool
================================================================================

🔍 DRY RUN MODE - No files will be deleted

🔍 Scanning for duplicate files...

📊 Found 3 sets of duplicate files:
================================================================================

🔑 Hash: a1b2c3d4e5f6g7h8...
   📦 Keeping: data.xlsx (ID: abc-123, 1,234,567 bytes)
   📤 Uploaded: 2025-09-28 10:00:00

   🗑️  Duplicates to remove:
      • data.xlsx
        ID: def-456
        Size: 1,234,567 bytes
        Uploaded: 2025-09-29 14:30:00
        Path: uploads/excel/def-456.xlsx

================================================================================
📈 Summary:
   • Total duplicate files: 5
   • Space to be saved: 10,234,567 bytes (9.76 MB)
================================================================================

🔒 DRY RUN MODE - No files were deleted
   Run with --execute flag to actually delete files
```

### Running in Production

```bash
# SSH or exec into backend pod
kubectl exec -it <backend-pod> -n agion-airgb -- /bin/sh

# Run dry run first
python scripts/remove_duplicate_files.py

# If satisfied with the preview, execute
python scripts/remove_duplicate_files.py --execute
```