"""Test script for file cleanup service."""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from src.config import config
from src.database.db_manager import init_database, get_db_manager
from src.utils.file_cleaner import init_cleanup_service

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


async def test_cleanup_service():
    """Test file cleanup service functionality."""
    print("=" * 60)
    print("Testing File Cleanup Service")
    print("=" * 60)

    # Initialize database
    db = init_database(config.DATABASE_PATH)
    print(f"✅ Database initialized at: {config.DATABASE_PATH}")

    # Initialize cleanup service
    cleanup_service = init_cleanup_service(cleanup_interval_hours=1)
    print(f"✅ Cleanup service initialized (interval: 1h)")

    # Get initial stats
    print("\n📊 Initial Statistics")
    stats = cleanup_service.get_stats()
    print(f"   Status: {'Running' if stats['is_running'] else 'Stopped'}")
    print(f"   Total runs: {stats['total_cleanup_runs']}")
    print(f"   Files deleted: {stats['total_files_deleted']}")
    print(f"   Space freed: {stats['total_space_freed_mb']:.2f} MB")

    # Test getting all users
    print("\n👥 Getting all users with settings...")
    users = await cleanup_service._get_all_users_with_settings(db)
    print(f"✅ Found {len(users)} users")

    for user_id, settings in users.items():
        auto_delete = settings.get('auto_delete_after_days', 0)
        print(f"   User {user_id}: auto-delete after {auto_delete} days")

    # Test manual cleanup
    print("\n🧹 Testing manual cleanup...")
    result = await cleanup_service.manual_cleanup()

    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    else:
        print("✅ Manual cleanup completed:")
        print(f"   Users cleaned: {result.get('users_cleaned', 0)}")
        print(f"   Files deleted: {result.get('files_deleted', 0)}")
        print(f"   Space freed: {result.get('space_freed_mb', 0):.2f} MB")

    # Final stats
    print("\n📊 Final Statistics")
    stats = cleanup_service.get_stats()
    print(f"   Total runs: {stats['total_cleanup_runs']}")
    print(f"   Files deleted: {stats['total_files_deleted']}")
    print(f"   Space freed: {stats['total_space_freed_mb']:.2f} MB")
    if stats['last_cleanup_time']:
        print(f"   Last cleanup: {stats['last_cleanup_time']}")

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


async def test_create_test_data():
    """Create test data for cleanup testing."""
    print("\n" + "=" * 60)
    print("Creating Test Data")
    print("=" * 60)

    db = get_db_manager()
    test_user_id = 123456789

    # Set auto-delete to 3 days
    await db.update_user_settings(test_user_id, auto_delete_after_days=3)
    print(f"✅ Set auto-delete to 3 days for user {test_user_id}")

    # Create test downloads dir
    test_dir = config.DOWNLOADS_DIR / "test_cleanup"
    test_dir.mkdir(exist_ok=True, parents=True)

    # Create old file (5 days ago)
    old_file = test_dir / "old_video.mp4"
    old_file.write_text("old test content")
    print(f"✅ Created old test file: {old_file}")

    # Add to history with old date
    old_date = (datetime.now() - timedelta(days=5)).isoformat()
    download_id = await db.add_download_history(
        user_id=test_user_id,
        url="https://test.com/old",
        platform="Instagram",
        content_type="video",
        file_path=str(old_file),
        file_size=len("old test content"),
        title="Old Test Video"
    )

    # Manually update date to be old
    import sqlite3
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE download_history SET download_date = ? WHERE id = ?",
        (old_date, download_id)
    )
    conn.commit()
    conn.close()

    print(f"✅ Added old download to history (ID: {download_id}, date: 5 days ago)")

    # Create new file (1 day ago)
    new_file = test_dir / "new_video.mp4"
    new_file.write_text("new test content")
    print(f"✅ Created new test file: {new_file}")

    # Add to history with recent date
    await db.add_download_history(
        user_id=test_user_id,
        url="https://test.com/new",
        platform="Instagram",
        content_type="video",
        file_path=str(new_file),
        file_size=len("new test content"),
        title="New Test Video"
    )

    print(f"✅ Added new download to history (date: today)")

    print("\n📁 Test data created:")
    print(f"   Old file (should be deleted): {old_file}")
    print(f"   New file (should be kept): {new_file}")
    print(f"   Auto-delete setting: 3 days")
    print(f"   Old file age: 5 days (should be deleted)")
    print(f"   New file age: 0 days (should be kept)")


async def main():
    """Main test function."""
    import sys

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        try:
            choice = input("\nChoose test:\n1. Test cleanup service\n2. Create test data\n3. Both\n\nChoice (1-3): ")
        except EOFError:
            choice = "1"  # Default to test cleanup

    if choice == "2":
        await test_create_test_data()
    elif choice == "3":
        await test_create_test_data()
        print("\nContinuing with cleanup test...")
        await test_cleanup_service()
    else:
        await test_cleanup_service()


if __name__ == "__main__":
    asyncio.run(main())
