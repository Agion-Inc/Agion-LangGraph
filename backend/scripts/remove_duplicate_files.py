"""
Remove Duplicate Files from Storage
Finds and removes duplicate files based on file hash, keeping the oldest one
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import AsyncSessionLocal, engine
from models import UploadedFile
from services.unified_storage import unified_storage


async def find_duplicates(db: AsyncSession):
    """Find all duplicate files based on hash"""
    print("🔍 Scanning for duplicate files...")

    # Get all files
    result = await db.execute(
        select(UploadedFile).order_by(UploadedFile.created_at)
    )
    all_files = result.scalars().all()

    # Group by hash
    files_by_hash = defaultdict(list)
    for file in all_files:
        if file.file_hash:
            files_by_hash[file.file_hash].append(file)

    # Find duplicates (hashes with more than one file)
    duplicates = {
        hash_val: files
        for hash_val, files in files_by_hash.items()
        if len(files) > 1
    }

    return duplicates


async def remove_duplicates(db: AsyncSession, dry_run: bool = True):
    """
    Remove duplicate files, keeping the oldest one

    Args:
        db: Database session
        dry_run: If True, only show what would be deleted without actually deleting
    """
    duplicates = await find_duplicates(db)

    if not duplicates:
        print("✅ No duplicate files found!")
        return

    print(f"\n📊 Found {len(duplicates)} sets of duplicate files:")
    print(f"{'='*80}")

    total_duplicates = 0
    total_space_saved = 0
    files_to_delete = []

    for hash_val, files in duplicates.items():
        # Sort by creation date (oldest first)
        files.sort(key=lambda f: f.created_at or datetime.min)

        # Keep the first (oldest) file
        keep_file = files[0]
        duplicate_files = files[1:]

        total_duplicates += len(duplicate_files)

        print(f"\n🔑 Hash: {hash_val[:16]}...")
        print(f"   📦 Keeping: {keep_file.filename} (ID: {keep_file.id}, {keep_file.file_size:,} bytes)")
        print(f"   📤 Uploaded: {keep_file.created_at}")
        print(f"\n   🗑️  Duplicates to remove:")

        for dup_file in duplicate_files:
            total_space_saved += dup_file.file_size
            files_to_delete.append(dup_file)

            print(f"      • {dup_file.filename}")
            print(f"        ID: {dup_file.id}")
            print(f"        Size: {dup_file.file_size:,} bytes")
            print(f"        Uploaded: {dup_file.created_at}")
            print(f"        Path: {dup_file.file_path}")

    print(f"\n{'='*80}")
    print(f"📈 Summary:")
    print(f"   • Total duplicate files: {total_duplicates}")
    print(f"   • Space to be saved: {total_space_saved:,} bytes ({total_space_saved / (1024*1024):.2f} MB)")
    print(f"{'='*80}\n")

    if dry_run:
        print("🔒 DRY RUN MODE - No files were deleted")
        print("   Run with --execute flag to actually delete files")
        return

    # Actually delete the files
    print("🗑️  Deleting duplicate files...")

    deleted_count = 0
    failed_count = 0

    for file in files_to_delete:
        try:
            # Delete from storage
            await unified_storage.delete_file(file.file_path)

            # Delete from database
            await db.delete(file)

            deleted_count += 1
            print(f"   ✅ Deleted: {file.filename} (ID: {file.id})")

        except Exception as e:
            failed_count += 1
            print(f"   ❌ Failed to delete {file.filename} (ID: {file.id}): {str(e)}")

    # Commit all deletions
    await db.commit()

    print(f"\n{'='*80}")
    print(f"✅ Cleanup completed!")
    print(f"   • Successfully deleted: {deleted_count} files")
    print(f"   • Failed: {failed_count} files")
    print(f"   • Space saved: {total_space_saved:,} bytes ({total_space_saved / (1024*1024):.2f} MB)")
    print(f"{'='*80}\n")


async def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Remove duplicate files from storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (preview what would be deleted)
  python scripts/remove_duplicate_files.py

  # Actually delete duplicates
  python scripts/remove_duplicate_files.py --execute
        """
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually delete files (default is dry run)'
    )

    args = parser.parse_args()

    print("\n" + "="*80)
    print("🧹 Duplicate File Cleanup Tool")
    print("="*80 + "\n")

    if args.execute:
        print("⚠️  EXECUTE MODE - Files will be permanently deleted!")
        print("   Press Ctrl+C within 5 seconds to cancel...\n")
        try:
            await asyncio.sleep(5)
        except KeyboardInterrupt:
            print("\n❌ Cancelled by user")
            return
    else:
        print("🔍 DRY RUN MODE - No files will be deleted\n")

    async with AsyncSessionLocal() as db:
        await remove_duplicates(db, dry_run=not args.execute)

    # Close engine
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())