"""Search functionality for download history."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.database.db_manager import get_db_manager

logger = logging.getLogger(__name__)


class HistorySearcher:
    """Search through download history with various filters."""

    @staticmethod
    async def search(
        user_id: int,
        query: Optional[str] = None,
        platform: Optional[str] = None,
        content_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        favorites_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search download history with multiple filters.

        Args:
            user_id: User ID
            query: Search query (searches in title, author, url)
            platform: Filter by platform (instagram, youtube, etc.)
            content_type: Filter by content type (video, photo, etc.)
            date_from: Filter by date from
            date_to: Filter by date to
            favorites_only: Show only favorites
            limit: Maximum results

        Returns:
            List of matching download records
        """
        db = get_db_manager()
        if not db:
            return []

        try:
            # Get all user history (we'll filter in Python for flexibility)
            all_history = await db.get_download_history(
                user_id=user_id,
                limit=10000,  # Get all
                platform=platform,  # Use DB filter for platform
                favorites_only=favorites_only  # Use DB filter for favorites
            )

            results = []

            for item in all_history:
                # Text search in title, author, URL
                if query:
                    query_lower = query.lower()
                    title = (item.get('title') or '').lower()
                    author = (item.get('author') or '').lower()
                    url = (item.get('url') or '').lower()

                    if not (query_lower in title or
                           query_lower in author or
                           query_lower in url):
                        continue

                # Content type filter
                if content_type:
                    item_type = item.get('content_type', '')
                    if item_type != content_type:
                        continue

                # Date range filter
                if date_from or date_to:
                    try:
                        item_date = datetime.fromisoformat(item['download_date'])

                        if date_from and item_date < date_from:
                            continue

                        if date_to and item_date > date_to:
                            continue

                    except (ValueError, TypeError, KeyError):
                        continue

                results.append(item)

                # Limit results
                if len(results) >= limit:
                    break

            logger.info(
                f"Search for user {user_id}: query='{query}', "
                f"platform={platform}, found {len(results)} results"
            )

            return results

        except Exception as e:
            logger.error(f"Error searching history: {e}", exc_info=True)
            return []

    @staticmethod
    async def search_by_date_range(
        user_id: int,
        days: int = 7,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search downloads from the last N days.

        Args:
            user_id: User ID
            days: Number of days to look back
            limit: Maximum results

        Returns:
            List of recent download records
        """
        date_from = datetime.now() - timedelta(days=days)

        return await HistorySearcher.search(
            user_id=user_id,
            date_from=date_from,
            limit=limit
        )

    @staticmethod
    async def search_by_author(
        user_id: int,
        author: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search downloads by author name.

        Args:
            user_id: User ID
            author: Author name to search
            limit: Maximum results

        Returns:
            List of matching download records
        """
        return await HistorySearcher.search(
            user_id=user_id,
            query=author,
            limit=limit
        )

    @staticmethod
    async def get_search_suggestions(user_id: int) -> Dict[str, Any]:
        """Get search suggestions based on user's history.

        Args:
            user_id: User ID

        Returns:
            Dictionary with suggestions (popular platforms, authors, etc.)
        """
        db = get_db_manager()
        if not db:
            return {}

        try:
            # Get all history
            history = await db.get_download_history(user_id, limit=10000)

            if not history:
                return {}

            # Collect statistics
            platforms = {}
            authors = {}
            content_types = {}

            for item in history:
                # Platform stats
                platform = item.get('platform', 'Unknown')
                platforms[platform] = platforms.get(platform, 0) + 1

                # Author stats
                author = item.get('author', '')
                if author:
                    authors[author] = authors.get(author, 0) + 1

                # Content type stats
                content_type = item.get('content_type', '')
                if content_type:
                    content_types[content_type] = content_types.get(content_type, 0) + 1

            # Get top items
            top_platforms = sorted(
                platforms.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            top_authors = sorted(
                authors.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

            top_content_types = sorted(
                content_types.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            return {
                'platforms': [p[0] for p in top_platforms],
                'authors': [a[0] for a in top_authors],
                'content_types': [c[0] for c in top_content_types],
                'total_downloads': len(history)
            }

        except Exception as e:
            logger.error(f"Error getting search suggestions: {e}")
            return {}

    @staticmethod
    def format_search_results(
        results: List[Dict[str, Any]],
        query: Optional[str] = None
    ) -> str:
        """Format search results for display.

        Args:
            results: List of search results
            query: Original search query

        Returns:
            Formatted text for Telegram
        """
        if not results:
            if query:
                return (
                    f"🔍 <b>Поиск: \"{query}\"</b>\n\n"
                    "❌ Ничего не найдено\n\n"
                    "💡 Попробуйте:\n"
                    "• Использовать другие ключевые слова\n"
                    "• Искать по автору или платформе\n"
                    "• Проверить правильность написания"
                )
            else:
                return "❌ Ничего не найдено"

        # Platform emoji mapping
        platform_emoji = {
            "instagram": "📸",
            "youtube": "📺",
            "tiktok": "🎵",
            "vk": "🎬",
            "twitter": "🐦",
            "facebook": "👤"
        }

        # Format header
        if query:
            text = f"🔍 <b>Результаты поиска: \"{query}\"</b>\n\n"
        else:
            text = f"🔍 <b>Найдено: {len(results)}</b>\n\n"

        # Format results
        for i, item in enumerate(results[:20], 1):  # Show max 20
            emoji = platform_emoji.get(item['platform'].lower(), "📁")

            # Date
            try:
                date = datetime.fromisoformat(item['download_date'])
                date_str = date.strftime("%d.%m %H:%M")
            except:
                date_str = "недавно"

            # Title
            title = (item.get('title') or "Без названия")[:35]
            if len(item.get('title') or "") > 35:
                title += "..."

            # Author
            author = item.get('author', '')
            author_str = f" • {author[:20]}" if author else ""

            # Size
            file_size = item.get('file_size', 0)
            size_mb = file_size / 1024 / 1024 if file_size > 0 else 0

            # Favorite mark
            favorite_mark = "⭐ " if item.get('is_favorite') else ""

            text += (
                f"{i}. {emoji} {favorite_mark}<b>{title}</b>\n"
                f"   {date_str}{author_str} • {size_mb:.1f} MB\n\n"
            )

        if len(results) > 20:
            text += f"\n💡 Показаны первые 20 из {len(results)} результатов"

        return text
