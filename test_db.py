"""Simple test script for database functionality."""
import asyncio
import sys
from pathlib import Path
from src.config import config
from src.database.db_manager import init_database

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


async def test_database():
    """Test basic database operations."""
    print("=" * 60)
    print("Testing Database Manager")
    print("=" * 60)

    # Initialize database
    db = init_database(config.DATABASE_PATH)
    print(f"✅ Database initialized at: {config.DATABASE_PATH}")

    # Test user settings
    print("\n📋 Test 1: User Settings")
    test_user_id = 123456789

    settings = await db.get_user_settings(test_user_id)
    print(f"✅ Default settings: {settings}")

    # Update settings
    await db.update_user_settings(
        test_user_id,
        default_quality='1080p',
        default_format='webm'
    )

    updated = await db.get_user_settings(test_user_id)
    print(f"✅ Updated settings: quality={updated['default_quality']}, format={updated['default_format']}")

    # Test download history
    print("\n📋 Test 2: Download History")
    download_id = await db.add_download_history(
        user_id=test_user_id,
        url="https://instagram.com/p/test123",
        platform="Instagram",
        content_type="video",
        file_path="/tmp/test.mp4",
        file_size=5242880,  # 5 MB
        title="Test Video",
        author="test_user"
    )
    print(f"✅ Download added with ID: {download_id}")

    # Get history
    history = await db.get_download_history(test_user_id, limit=10)
    print(f"✅ History count: {len(history)}")
    if history:
        print(f"   Latest: {history[0]['title']} ({history[0]['platform']})")

    # Test favorites
    print("\n📋 Test 3: Favorites")
    if download_id:
        success = await db.add_to_favorites(download_id)
        print(f"✅ Added to favorites: {success}")

        favorites = await db.get_download_history(test_user_id, favorites_only=True)
        print(f"✅ Favorites count: {len(favorites)}")

    # Test collections
    print("\n📋 Test 4: Collections")
    collection_id = await db.create_collection(
        user_id=test_user_id,
        name="Test Collection",
        description="My test collection",
        icon="📸"
    )
    print(f"✅ Collection created with ID: {collection_id}")

    collections = await db.get_collections(test_user_id)
    print(f"✅ Collections count: {len(collections)}")
    if collections:
        print(f"   Latest: {collections[0]['icon']} {collections[0]['name']}")

    # Add to collection
    if download_id and collection_id:
        success = await db.add_to_collection(download_id, collection_id)
        print(f"✅ Added to collection: {success}")

        items = await db.get_collection_items(collection_id)
        print(f"✅ Collection items: {len(items)}")

    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
    print(f"\nDatabase file: {config.DATABASE_PATH}")
    print(f"Database size: {config.DATABASE_PATH.stat().st_size / 1024:.2f} KB")


if __name__ == "__main__":
    asyncio.run(test_database())
