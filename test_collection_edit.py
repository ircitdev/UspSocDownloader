"""Test script for collection editing functionality."""
import asyncio
import sys
from src.config import config
from src.database.db_manager import init_database, get_db_manager

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


async def test_collection_edit():
    """Test collection editing."""
    print("=" * 60)
    print("Testing Collection Editing")
    print("=" * 60)

    # Initialize database
    db = init_database(config.DATABASE_PATH)
    print(f"✅ Database initialized at: {config.DATABASE_PATH}")

    test_user_id = 123456789

    # Test 1: Create collection
    print("\n📋 Test 1: Create collection")
    collection_id = await db.create_collection(
        user_id=test_user_id,
        name="Test Collection",
        description="Test description",
        icon="📁"
    )
    print(f"✅ Created collection ID: {collection_id}")

    # Test 2: Get collection
    print("\n📋 Test 2: Get collection")
    collection = await db.get_collection_by_id(collection_id)
    print(f"✅ Collection details:")
    print(f"   Name: {collection['name']}")
    print(f"   Icon: {collection['icon']}")
    print(f"   Description: {collection['description']}")

    # Test 3: Update collection name
    print("\n📋 Test 3: Update collection name")
    success = await db.update_collection(
        collection_id=collection_id,
        name="Renamed Collection"
    )
    print(f"✅ Update successful: {success}")

    collection = await db.get_collection_by_id(collection_id)
    print(f"   New name: {collection['name']}")

    # Test 4: Update collection icon
    print("\n📋 Test 4: Update collection icon")
    success = await db.update_collection(
        collection_id=collection_id,
        icon="🎬"
    )
    print(f"✅ Update successful: {success}")

    collection = await db.get_collection_by_id(collection_id)
    print(f"   New icon: {collection['icon']}")

    # Test 5: Update both name and icon
    print("\n📋 Test 5: Update both name and icon")
    success = await db.update_collection(
        collection_id=collection_id,
        name="Final Name",
        icon="📸"
    )
    print(f"✅ Update successful: {success}")

    collection = await db.get_collection_by_id(collection_id)
    print(f"   Final name: {collection['name']}")
    print(f"   Final icon: {collection['icon']}")

    # Test 6: Get all collections
    print("\n📋 Test 6: Get all user collections")
    collections = await db.get_collections(test_user_id)
    print(f"✅ Found {len(collections)} collections:")
    for col in collections:
        print(f"   {col['icon']} {col['name']} (ID: {col['id']})")

    # Test 7: Delete collection
    print("\n📋 Test 7: Delete collection")
    success = await db.delete_collection(collection_id)
    print(f"✅ Delete successful: {success}")

    # Verify deletion
    collection = await db.get_collection_by_id(collection_id)
    print(f"   Collection exists after delete: {collection is not None}")

    print("\n" + "=" * 60)
    print("✅ All collection editing tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_collection_edit())
