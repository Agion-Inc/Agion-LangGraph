"""
Migration Script: BLOB Storage to File System
Migrates existing files from database BLOB storage to organized file system
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import AsyncSessionLocal, init_db
from models import UploadedFile as OldUploadedFile
from models_v2 import UploadedFile as NewUploadedFile
from services.file_storage import storage_service
import aiofiles


async def migrate_files():
    """Migrate files from BLOB storage to file system"""
    print("🚀 Starting migration: BLOB storage → File system")
    print("=" * 60)
    
    # Initialize database
    await init_db()
    
    async with AsyncSessionLocal() as db:
        try:
            # Get all files with BLOB content
            result = await db.execute(select(OldUploadedFile))
            old_files = result.scalars().all()
            
            total_files = len(old_files)
            print(f"📊 Found {total_files} files to migrate")
            print()
            
            if total_files == 0:
                print("✅ No files to migrate - database is clean!")
                return
            
            migrated = 0
            errors = 0
            skipped = 0
            
            for idx, old_file in enumerate(old_files, 1):
                print(f"[{idx}/{total_files}] Processing: {old_file.filename}")
                
                try:
                    # Check if file has BLOB content
                    if not hasattr(old_file, 'file_content') or not old_file.file_content:
                        print(f"  ⚠️  Skipped: No BLOB content found")
                        skipped += 1
                        continue
                    
                    # Determine file category
                    extension = '.' + old_file.filename.split('.')[-1].lower()
                    category_map = {
                        '.xlsx': 'excel',
                        '.xls': 'excel',
                        '.csv': 'csv',
                        '.json': 'json',
                        '.parquet': 'parquet',
                    }
                    category = category_map.get(extension, 'other')
                    
                    # Generate file path
                    from datetime import datetime
                    date_path = old_file.created_at.strftime("%Y/%m/%d")
                    file_path = storage_service.base_path / "uploads" / category / date_path / f"{old_file.id}{extension}"
                    
                    # Create directory if it doesn't exist
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write BLOB content to file
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(old_file.file_content)
                    
                    # Calculate file hash
                    file_hash = await storage_service._calculate_file_hash(file_path)
                    
                    # Get relative path
                    relative_path = str(file_path.relative_to(storage_service.base_path))
                    
                    # Update file record (remove BLOB, add new fields)
                    old_file.file_path = relative_path
                    old_file.file_hash = file_hash
                    old_file.category = category
                    if not hasattr(old_file, 'upload_source'):
                        old_file.upload_source = 'migrated'
                    
                    # Clear BLOB content to free up database space
                    if hasattr(old_file, 'file_content'):
                        old_file.file_content = None
                    
                    await db.commit()
                    
                    print(f"  ✅ Migrated: {relative_path}")
                    print(f"     Size: {old_file.file_size:,} bytes")
                    print(f"     Hash: {file_hash[:16]}...")
                    migrated += 1
                    
                except Exception as e:
                    print(f"  ❌ Error: {str(e)}")
                    errors += 1
                    await db.rollback()
                
                print()
            
            # Print summary
            print("=" * 60)
            print("📊 Migration Summary:")
            print(f"   Total files: {total_files}")
            print(f"   ✅ Migrated: {migrated}")
            print(f"   ⚠️  Skipped:  {skipped}")
            print(f"   ❌ Errors:   {errors}")
            print()
            
            if errors == 0:
                print("🎉 Migration completed successfully!")
            else:
                print(f"⚠️  Migration completed with {errors} error(s)")
                print("   Review errors above and run migration again if needed")
            
            # Get storage stats
            stats = await storage_service.get_storage_stats()
            print()
            print("📦 Storage Statistics:")
            print(f"   Total files: {stats['total_files']}")
            print(f"   Total size:  {stats['total_size']:,} bytes ({stats['total_size'] / (1024 * 1024):.2f} MB)")
            print(f"   Categories:  {list(stats['categories'].keys())}")
            
        except Exception as e:
            print(f"❌ Fatal error during migration: {str(e)}")
            raise


async def verify_migration():
    """Verify that migration was successful"""
    print("\n" + "=" * 60)
    print("🔍 Verifying migration...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        try:
            # Check all files have file_path and file_hash
            result = await db.execute(select(OldUploadedFile))
            files = result.scalars().all()
            
            issues = []
            
            for file in files:
                # Check file_path exists
                if not file.file_path:
                    issues.append(f"File {file.id} ({file.filename}): Missing file_path")
                    continue
                
                # Check file exists on disk
                full_path = storage_service.base_path / file.file_path
                if not full_path.exists():
                    issues.append(f"File {file.id} ({file.filename}): File not found at {file.file_path}")
                
                # Check file_hash exists
                if not hasattr(file, 'file_hash') or not file.file_hash:
                    issues.append(f"File {file.id} ({file.filename}): Missing file_hash")
            
            if issues:
                print("⚠️  Verification found issues:")
                for issue in issues:
                    print(f"   - {issue}")
                print()
                print("❌ Verification failed - please review issues above")
                return False
            else:
                print("✅ Verification passed - all files migrated correctly!")
                return True
                
        except Exception as e:
            print(f"❌ Verification error: {str(e)}")
            return False


async def main():
    """Main migration function"""
    try:
        await migrate_files()
        success = await verify_migration()
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 Migration and verification completed successfully!")
            print()
            print("Next steps:")
            print("1. Test file upload: POST /api/v1/files/upload")
            print("2. Test file listing: GET /api/v1/files")
            print("3. Test file download: GET /api/v1/files/{file_id}/download")
            print("4. Update frontend to use new endpoints")
            print("5. Deploy to staging for testing")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n⚠️  Migration completed with issues - review and retry")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
