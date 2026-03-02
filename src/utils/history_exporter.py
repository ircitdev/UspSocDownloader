"""History export functionality - CSV and JSON formats."""
import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from io import StringIO

logger = logging.getLogger(__name__)


class HistoryExporter:
    """Export download history to various formats."""

    @staticmethod
    def to_csv(history: List[Dict[str, Any]], include_metadata: bool = True) -> str:
        """Export history to CSV format.

        Args:
            history: List of download records
            include_metadata: Include extended metadata columns

        Returns:
            CSV string
        """
        if not history:
            return ""

        output = StringIO()

        # Define columns
        if include_metadata:
            fieldnames = [
                'id', 'date', 'platform', 'title', 'author', 'url',
                'content_type', 'file_size_mb', 'is_favorite'
            ]
        else:
            fieldnames = ['date', 'platform', 'title', 'author', 'url']

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for item in history:
            row = {}

            # Parse date
            try:
                date = datetime.fromisoformat(item['download_date'])
                row['date'] = date.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                row['date'] = item['download_date']

            # Basic fields
            row['platform'] = item.get('platform', '')
            row['title'] = item.get('title', 'Без названия')
            row['author'] = item.get('author', '')
            row['url'] = item.get('url', '')

            # Extended metadata
            if include_metadata:
                row['id'] = item.get('id', '')
                row['content_type'] = item.get('content_type', '')

                # File size in MB
                file_size = item.get('file_size', 0)
                if file_size:
                    row['file_size_mb'] = f"{file_size / 1024 / 1024:.2f}"
                else:
                    row['file_size_mb'] = ''

                row['is_favorite'] = 'Да' if item.get('is_favorite') else 'Нет'

            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def to_json(
        history: List[Dict[str, Any]],
        pretty: bool = True,
        include_file_paths: bool = False
    ) -> str:
        """Export history to JSON format.

        Args:
            history: List of download records
            pretty: Pretty-print JSON (indented)
            include_file_paths: Include local file paths

        Returns:
            JSON string
        """
        if not history:
            return "[]"

        # Prepare data
        export_data = []

        for item in history:
            record = {
                'id': item.get('id'),
                'download_date': item.get('download_date'),
                'platform': item.get('platform'),
                'content_type': item.get('content_type'),
                'title': item.get('title'),
                'author': item.get('author'),
                'url': item.get('url'),
                'thumbnail_url': item.get('thumbnail_url'),
                'is_favorite': bool(item.get('is_favorite')),
            }

            # File size in bytes and MB
            file_size = item.get('file_size', 0)
            if file_size:
                record['file_size_bytes'] = file_size
                record['file_size_mb'] = round(file_size / 1024 / 1024, 2)

            # Optional file path
            if include_file_paths and item.get('file_path'):
                record['file_path'] = item.get('file_path')

            # Collection info
            if item.get('collection_id'):
                record['collection_id'] = item.get('collection_id')

            export_data.append(record)

        # Convert to JSON
        if pretty:
            return json.dumps(export_data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(export_data, ensure_ascii=False)

    @staticmethod
    def generate_filename(user_id: int, format_type: str) -> str:
        """Generate filename for export.

        Args:
            user_id: User ID
            format_type: 'csv' or 'json'

        Returns:
            Filename string
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"download_history_{user_id}_{timestamp}.{format_type}"

    @staticmethod
    def save_to_file(
        content: str,
        file_path: Path,
        encoding: str = 'utf-8'
    ) -> bool:
        """Save export content to file.

        Args:
            content: Export content
            file_path: Path to save file
            encoding: File encoding (default: utf-8)

        Returns:
            True if successful
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding=encoding)
            logger.info(f"Exported history to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save export to {file_path}: {e}")
            return False

    @staticmethod
    def get_export_stats(history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about export data.

        Args:
            history: List of download records

        Returns:
            Dictionary with statistics
        """
        if not history:
            return {
                'total_downloads': 0,
                'total_size_mb': 0,
                'platforms': {},
                'favorites': 0,
                'date_range': None
            }

        # Count by platform
        platforms = {}
        total_size = 0
        favorites = 0

        for item in history:
            # Platform count
            platform = item.get('platform', 'Unknown')
            platforms[platform] = platforms.get(platform, 0) + 1

            # Total size
            file_size = item.get('file_size', 0)
            if file_size:
                total_size += file_size

            # Favorites
            if item.get('is_favorite'):
                favorites += 1

        # Date range
        dates = []
        for item in history:
            try:
                date = datetime.fromisoformat(item['download_date'])
                dates.append(date)
            except (ValueError, TypeError):
                pass

        date_range = None
        if dates:
            dates.sort()
            date_range = {
                'first': dates[0].strftime('%Y-%m-%d'),
                'last': dates[-1].strftime('%Y-%m-%d')
            }

        return {
            'total_downloads': len(history),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'platforms': platforms,
            'favorites': favorites,
            'date_range': date_range
        }


# Helper function for quick export
async def export_user_history(
    db,
    user_id: int,
    format_type: str = 'json',
    limit: Optional[int] = None,
    platform: Optional[str] = None,
    favorites_only: bool = False
) -> tuple[str, Dict[str, Any]]:
    """Export user history to specified format.

    Args:
        db: DatabaseManager instance
        user_id: User ID
        format_type: 'csv' or 'json'
        limit: Maximum records (None = all)
        platform: Filter by platform (None = all)
        favorites_only: Export only favorites

    Returns:
        Tuple of (content_string, stats_dict)
    """
    # Get history from database
    history = await db.get_download_history(
        user_id=user_id,
        limit=limit or 10000,
        platform=platform,
        favorites_only=favorites_only
    )

    # Generate export
    exporter = HistoryExporter()

    if format_type.lower() == 'csv':
        content = exporter.to_csv(history, include_metadata=True)
    else:  # json
        content = exporter.to_json(history, pretty=True, include_file_paths=False)

    # Get statistics
    stats = exporter.get_export_stats(history)

    return content, stats
