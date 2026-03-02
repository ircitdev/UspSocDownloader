"""Comprehensive unit tests for UspSocDownloader bot."""
import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.database.db_manager import init_database, get_db_manager
from src.utils.history_exporter import HistoryExporter, export_user_history
from src.utils.history_search import HistorySearcher
from src.utils.file_cleaner import FileCleanupService

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class TestRunner:
    """Test runner for all components."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def assert_true(self, condition, test_name):
        """Assert condition is true."""
        if condition:
            self.passed += 1
            print(f"✅ {test_name}")
        else:
            self.failed += 1
            self.errors.append(test_name)
            print(f"❌ {test_name}")

    def assert_equal(self, actual, expected, test_name):
        """Assert values are equal."""
        if actual == expected:
            self.passed += 1
            print(f"✅ {test_name}")
        else:
            self.failed += 1
            self.errors.append(f"{test_name} (expected: {expected}, got: {actual})")
            print(f"❌ {test_name}")

    def assert_not_none(self, value, test_name):
        """Assert value is not None."""
        if value is not None:
            self.passed += 1
            print(f"✅ {test_name}")
        else:
            self.failed += 1
            self.errors.append(test_name)
            print(f"❌ {test_name}")

    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total tests: {total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")

        if self.failed > 0:
            print(f"\nFailed tests:")
            for error in self.errors:
                print(f"  • {error}")

        success_rate = (self.passed / total * 100) if total > 0 else 0
        print(f"\nSuccess rate: {success_rate:.1f}%")
        print("=" * 60)


async def test_database():
    """Test database functionality."""
    print("\n" + "=" * 60)
    print("1. DATABASE TESTS")
    print("=" * 60)

    runner = TestRunner()

    # Initialize database
    db = init_database(config.DATABASE_PATH)
    runner.assert_not_none(db, "Database initialization")

    test_user_id = 999999999  # Test user

    # Test user settings
    settings = await db.get_user_settings(test_user_id)
    runner.assert_not_none(settings, "Get user settings")
    runner.assert_equal(settings['default_quality'], '720p', "Default quality is 720p")

    # Update settings
    success = await db.update_user_settings(test_user_id, default_quality='1080p')
    runner.assert_true(success, "Update user settings")

    updated = await db.get_user_settings(test_user_id)
    runner.assert_equal(updated['default_quality'], '1080p', "Quality updated to 1080p")

    # Test download history
    download_id = await db.add_download_history(
        user_id=test_user_id,
        url="https://test.com/video",
        platform="YouTube",
        content_type="video",
        title="Test Video",
        file_size=1024000
    )
    runner.assert_not_none(download_id, "Add download to history")

    history = await db.get_download_history(test_user_id, limit=10)
    runner.assert_true(len(history) > 0, "Get download history")

    # Test favorites
    success = await db.add_to_favorites(download_id)
    runner.assert_true(success, "Add to favorites")

    favorites = await db.get_download_history(test_user_id, favorites_only=True)
    runner.assert_true(len(favorites) > 0, "Get favorites")

    # Test collections
    collection_id = await db.create_collection(
        user_id=test_user_id,
        name="Test Collection",
        icon="📁"
    )
    runner.assert_not_none(collection_id, "Create collection")

    collections = await db.get_collections(test_user_id)
    runner.assert_true(len(collections) > 0, "Get collections")

    # Test collection update
    success = await db.update_collection(
        collection_id=collection_id,
        name="Updated Collection"
    )
    runner.assert_true(success, "Update collection name")

    updated_collection = await db.get_collection_by_id(collection_id)
    runner.assert_equal(updated_collection['name'], "Updated Collection", "Collection name updated")

    # Cleanup
    await db.delete_collection(collection_id)

    runner.print_summary()
    return runner.failed == 0


async def test_export():
    """Test export functionality."""
    print("\n" + "=" * 60)
    print("2. EXPORT TESTS")
    print("=" * 60)

    runner = TestRunner()
    db = get_db_manager()
    test_user_id = 999999999

    # Test CSV export
    csv_content, csv_stats = await export_user_history(
        db=db,
        user_id=test_user_id,
        format_type='csv'
    )
    runner.assert_not_none(csv_content, "CSV export generated")
    runner.assert_true(len(csv_content) > 0, "CSV content not empty")
    runner.assert_true('id,date,platform' in csv_content, "CSV has headers")

    # Test JSON export
    json_content, json_stats = await export_user_history(
        db=db,
        user_id=test_user_id,
        format_type='json'
    )
    runner.assert_not_none(json_content, "JSON export generated")
    runner.assert_true(len(json_content) > 0, "JSON content not empty")
    runner.assert_true('[' in json_content and ']' in json_content, "JSON is array")

    # Test export stats
    runner.assert_not_none(csv_stats.get('total_downloads'), "Stats have total_downloads")
    runner.assert_not_none(csv_stats.get('platforms'), "Stats have platforms")

    # Test export formatting
    exporter = HistoryExporter()
    filename = exporter.generate_filename(test_user_id, 'csv')
    runner.assert_true(filename.endswith('.csv'), "CSV filename has .csv extension")
    runner.assert_true(str(test_user_id) in filename, "Filename contains user ID")

    runner.print_summary()
    return runner.failed == 0


async def test_search():
    """Test search functionality."""
    print("\n" + "=" * 60)
    print("3. SEARCH TESTS")
    print("=" * 60)

    runner = TestRunner()
    test_user_id = 999999999

    # Test text search
    results = await HistorySearcher.search(
        user_id=test_user_id,
        query="test"
    )
    runner.assert_not_none(results, "Text search returns results")

    # Test platform search
    results = await HistorySearcher.search(
        user_id=test_user_id,
        platform="YouTube"
    )
    runner.assert_not_none(results, "Platform search returns results")

    # Test date range search
    results = await HistorySearcher.search_by_date_range(
        user_id=test_user_id,
        days=30
    )
    runner.assert_not_none(results, "Date range search returns results")

    # Test search suggestions
    suggestions = await HistorySearcher.get_search_suggestions(test_user_id)
    runner.assert_not_none(suggestions, "Search suggestions generated")
    runner.assert_true('platforms' in suggestions, "Suggestions have platforms")
    runner.assert_true('total_downloads' in suggestions, "Suggestions have total_downloads")

    # Test result formatting
    formatted = HistorySearcher.format_search_results(results, "test")
    runner.assert_not_none(formatted, "Results formatted")
    runner.assert_true(len(formatted) > 0, "Formatted text not empty")

    runner.print_summary()
    return runner.failed == 0


async def test_cleanup_service():
    """Test file cleanup service."""
    print("\n" + "=" * 60)
    print("4. FILE CLEANUP TESTS")
    print("=" * 60)

    runner = TestRunner()

    # Initialize service
    service = FileCleanupService(cleanup_interval_hours=1)
    runner.assert_not_none(service, "Cleanup service initialized")

    # Test stats
    stats = service.get_stats()
    runner.assert_not_none(stats, "Get stats")
    runner.assert_equal(stats['is_running'], False, "Service not running initially")
    runner.assert_equal(stats['cleanup_interval_hours'], 1, "Interval is 1 hour")

    # Test manual cleanup
    db = get_db_manager()
    result = await service.manual_cleanup(user_id=999999999)
    runner.assert_not_none(result, "Manual cleanup executed")
    runner.assert_true('files_deleted' in result, "Result has files_deleted")

    runner.print_summary()
    return runner.failed == 0


async def run_all_tests():
    """Run all tests."""
    print("\n" + "█" * 60)
    print("USPSOCDOWNLOADER - COMPREHENSIVE TEST SUITE")
    print("█" * 60)

    results = []

    # Run all test suites
    results.append(await test_database())
    results.append(await test_export())
    results.append(await test_search())
    results.append(await test_cleanup_service())

    # Final summary
    print("\n" + "█" * 60)
    print("FINAL RESULTS")
    print("█" * 60)

    passed_suites = sum(results)
    total_suites = len(results)

    print(f"Test Suites Passed: {passed_suites}/{total_suites}")

    if passed_suites == total_suites:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        return True
    else:
        print(f"\n⚠️  {total_suites - passed_suites} TEST SUITE(S) FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
