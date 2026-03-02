"""Test script for history export functionality."""
import asyncio
import sys
from pathlib import Path
from src.config import config
from src.database.db_manager import init_database, get_db_manager
from src.utils.history_exporter import export_user_history, HistoryExporter

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


async def test_export():
    """Test export functionality."""
    print("=" * 60)
    print("Testing History Export")
    print("=" * 60)

    # Initialize database
    db = init_database(config.DATABASE_PATH)
    print(f"✅ Database initialized at: {config.DATABASE_PATH}")

    # Get test user history
    test_user_id = 123456789
    history = await db.get_download_history(test_user_id, limit=100)

    if not history:
        print(f"\n❌ No history found for user {test_user_id}")
        print("Run the bot and download something first!")
        return

    print(f"\n📊 Found {len(history)} downloads for user {test_user_id}")

    # Test CSV export
    print("\n📄 Testing CSV export...")
    csv_content, csv_stats = await export_user_history(
        db=db,
        user_id=test_user_id,
        format_type='csv'
    )

    print(f"✅ CSV generated:")
    print(f"   Records: {csv_stats['total_downloads']}")
    print(f"   Size: {csv_stats['total_size_mb']:.2f} MB")
    print(f"   Platforms: {csv_stats['platforms']}")
    print(f"   Favorites: {csv_stats['favorites']}")

    # Show sample
    lines = csv_content.split('\n')
    print(f"\n📋 CSV Preview (first 5 lines):")
    for i, line in enumerate(lines[:5], 1):
        print(f"   {i}. {line}")

    # Save CSV
    exporter = HistoryExporter()
    csv_path = config.DATA_DIR / "exports" / f"test_export_{test_user_id}.csv"
    if exporter.save_to_file(csv_content, csv_path):
        print(f"\n✅ CSV saved to: {csv_path}")
        print(f"   File size: {csv_path.stat().st_size / 1024:.2f} KB")

    # Test JSON export
    print("\n📋 Testing JSON export...")
    json_content, json_stats = await export_user_history(
        db=db,
        user_id=test_user_id,
        format_type='json'
    )

    print(f"✅ JSON generated:")
    print(f"   Records: {json_stats['total_downloads']}")
    print(f"   Size: {json_stats['total_size_mb']:.2f} MB")

    # Show sample
    import json
    data = json.loads(json_content)
    print(f"\n📋 JSON Preview (first record):")
    if data:
        first_record = data[0]
        for key, value in first_record.items():
            print(f"   {key}: {value}")

    # Save JSON
    json_path = config.DATA_DIR / "exports" / f"test_export_{test_user_id}.json"
    if exporter.save_to_file(json_content, json_path):
        print(f"\n✅ JSON saved to: {json_path}")
        print(f"   File size: {json_path.stat().st_size / 1024:.2f} KB")

    # Test favorites export
    print("\n⭐ Testing favorites export...")
    fav_content, fav_stats = await export_user_history(
        db=db,
        user_id=test_user_id,
        format_type='csv',
        favorites_only=True
    )

    print(f"✅ Favorites CSV generated:")
    print(f"   Favorites: {fav_stats['total_downloads']}")

    if fav_stats['total_downloads'] > 0:
        fav_path = config.DATA_DIR / "exports" / f"test_favorites_{test_user_id}.csv"
        if exporter.save_to_file(fav_content, fav_path):
            print(f"   Saved to: {fav_path}")
    else:
        print("   No favorites to export")

    # Test platform export
    if csv_stats.get('platforms'):
        platform = list(csv_stats['platforms'].keys())[0]
        print(f"\n📱 Testing platform export ({platform})...")

        plat_content, plat_stats = await export_user_history(
            db=db,
            user_id=test_user_id,
            format_type='csv',
            platform=platform
        )

        print(f"✅ Platform CSV generated:")
        print(f"   Platform: {platform}")
        print(f"   Records: {plat_stats['total_downloads']}")

        if plat_stats['total_downloads'] > 0:
            plat_path = config.DATA_DIR / "exports" / f"test_{platform}_{test_user_id}.csv"
            if exporter.save_to_file(plat_content, plat_path):
                print(f"   Saved to: {plat_path}")

    print("\n" + "=" * 60)
    print("✅ All export tests completed!")
    print("=" * 60)

    # Show export directory
    export_dir = config.DATA_DIR / "exports"
    if export_dir.exists():
        files = list(export_dir.glob("test_*"))
        if files:
            print(f"\n📁 Exported files ({len(files)}):")
            for f in files:
                size_kb = f.stat().st_size / 1024
                print(f"   • {f.name} ({size_kb:.2f} KB)")


if __name__ == "__main__":
    asyncio.run(test_export())
