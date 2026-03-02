"""Test script for history search functionality."""
import asyncio
import sys
from datetime import datetime, timedelta
from src.config import config
from src.database.db_manager import init_database, get_db_manager
from src.utils.history_search import HistorySearcher

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


async def create_test_data():
    """Create test data for search testing."""
    print("=" * 60)
    print("Creating Test Data for Search")
    print("=" * 60)

    # Initialize database
    init_database(config.DATABASE_PATH)
    db = get_db_manager()
    test_user_id = 123456789

    # Add multiple test downloads
    test_downloads = [
        {
            "url": "https://instagram.com/p/test1",
            "platform": "Instagram",
            "title": "Beautiful sunset in Paris",
            "author": "photographer_john",
            "content_type": "photo",
            "date_offset": 1  # 1 day ago
        },
        {
            "url": "https://youtube.com/watch?v=test2",
            "platform": "YouTube",
            "title": "Python tutorial for beginners",
            "author": "tech_guru",
            "content_type": "video",
            "date_offset": 3  # 3 days ago
        },
        {
            "url": "https://instagram.com/p/test3",
            "platform": "Instagram",
            "title": "Cute cat playing",
            "author": "cat_lover_123",
            "content_type": "video",
            "date_offset": 7  # 7 days ago
        },
        {
            "url": "https://tiktok.com/@user/test4",
            "platform": "TikTok",
            "title": "Dance challenge",
            "author": "dancer_pro",
            "content_type": "video",
            "date_offset": 10  # 10 days ago
        },
        {
            "url": "https://youtube.com/watch?v=test5",
            "platform": "YouTube",
            "title": "Paris travel vlog",
            "author": "travel_blogger",
            "content_type": "video",
            "date_offset": 15  # 15 days ago
        }
    ]

    import sqlite3

    for item in test_downloads:
        # Add to history
        download_date = datetime.now() - timedelta(days=item['date_offset'])

        download_id = await db.add_download_history(
            user_id=test_user_id,
            url=item['url'],
            platform=item['platform'],
            content_type=item['content_type'],
            title=item['title'],
            author=item['author'],
            file_size=5242880  # 5 MB
        )

        # Update date manually
        conn = sqlite3.connect(config.DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE download_history SET download_date = ? WHERE id = ?",
            (download_date.isoformat(), download_id)
        )
        conn.commit()
        conn.close()

        print(f"✅ Added: {item['title']} ({item['date_offset']} days ago)")

    print(f"\n✅ Created {len(test_downloads)} test downloads")


async def test_search():
    """Test search functionality."""
    print("\n" + "=" * 60)
    print("Testing Search Functionality")
    print("=" * 60)

    # Initialize database
    db = init_database(config.DATABASE_PATH)
    print(f"✅ Database initialized at: {config.DATABASE_PATH}")

    test_user_id = 123456789

    # Test 1: Text search
    print("\n🔍 Test 1: Text search for 'Paris'")
    results = await HistorySearcher.search(
        user_id=test_user_id,
        query="Paris"
    )
    print(f"✅ Found {len(results)} results")
    for r in results:
        print(f"   • {r['title']} ({r['platform']})")

    # Test 2: Platform search
    print("\n🔍 Test 2: Search by platform (Instagram)")
    results = await HistorySearcher.search(
        user_id=test_user_id,
        platform="Instagram"
    )
    print(f"✅ Found {len(results)} results")
    for r in results:
        print(f"   • {r['title']}")

    # Test 3: Date range search
    print("\n🔍 Test 3: Search last 7 days")
    results = await HistorySearcher.search_by_date_range(
        user_id=test_user_id,
        days=7
    )
    print(f"✅ Found {len(results)} results")
    for r in results:
        date = datetime.fromisoformat(r['download_date'])
        print(f"   • {r['title']} ({date.strftime('%d.%m')})")

    # Test 4: Content type search
    print("\n🔍 Test 4: Search by content type (video)")
    results = await HistorySearcher.search(
        user_id=test_user_id,
        content_type="video"
    )
    print(f"✅ Found {len(results)} results")
    for r in results:
        print(f"   • {r['title']} ({r['platform']})")

    # Test 5: Author search
    print("\n🔍 Test 5: Search by author")
    results = await HistorySearcher.search_by_author(
        user_id=test_user_id,
        author="tech"
    )
    print(f"✅ Found {len(results)} results")
    for r in results:
        print(f"   • {r['title']} by {r['author']}")

    # Test 6: Get suggestions
    print("\n🔍 Test 6: Get search suggestions")
    suggestions = await HistorySearcher.get_search_suggestions(test_user_id)
    print(f"✅ Suggestions generated:")
    print(f"   Total downloads: {suggestions['total_downloads']}")
    print(f"   Platforms: {', '.join(suggestions['platforms'])}")
    print(f"   Top authors: {', '.join(suggestions['authors'][:3])}")
    print(f"   Content types: {', '.join(suggestions['content_types'])}")

    # Test 7: Format results
    print("\n🔍 Test 7: Format search results")
    results = await HistorySearcher.search(
        user_id=test_user_id,
        query="video",
        limit=3
    )
    formatted = HistorySearcher.format_search_results(results, "video")
    print("✅ Formatted output:")
    print(formatted)

    # Test 8: Empty search
    print("\n🔍 Test 8: Search with no results")
    results = await HistorySearcher.search(
        user_id=test_user_id,
        query="nonexistent_query_xyz"
    )
    formatted = HistorySearcher.format_search_results(results, "nonexistent_query_xyz")
    print(f"✅ Found {len(results)} results")
    print(formatted)

    print("\n" + "=" * 60)
    print("✅ All search tests completed!")
    print("=" * 60)


async def main():
    """Main test function."""
    import sys

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        try:
            choice = input("\nChoose test:\n1. Test search\n2. Create test data\n3. Both\n\nChoice (1-3): ")
        except EOFError:
            choice = "1"

    if choice == "2":
        await create_test_data()
    elif choice == "3":
        await create_test_data()
        print("\nContinuing with search tests...")
        await test_search()
    else:
        await test_search()


if __name__ == "__main__":
    asyncio.run(main())
