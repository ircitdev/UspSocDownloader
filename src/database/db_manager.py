"""Database manager for user settings, download history, and collections."""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)


def async_db_operation(func):
    """Decorator to run database operations in executor."""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(self, *args, **kwargs))
    return wrapper


class DatabaseManager:
    """Manages SQLite database for bot data."""

    def __init__(self, db_path: Path):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database with required tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # User settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    default_quality TEXT DEFAULT '720p',
                    default_format TEXT DEFAULT 'mp4',
                    language TEXT DEFAULT 'ru',
                    auto_delete_after_days INTEGER DEFAULT 7,
                    notifications_enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Download history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS download_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    content_type TEXT,
                    file_path TEXT,
                    file_size INTEGER,
                    title TEXT,
                    author TEXT,
                    thumbnail_url TEXT,
                    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_favorite BOOLEAN DEFAULT FALSE,
                    collection_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES user_settings(user_id),
                    FOREIGN KEY (collection_id) REFERENCES collections(id)
                )
            """)

            # Collections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    icon TEXT DEFAULT '📁',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_settings(user_id)
                )
            """)

            # Create indices for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_user_id
                ON download_history(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_date
                ON download_history(download_date DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_platform
                ON download_history(platform)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_collections_user_id
                ON collections(user_id)
            """)

            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @async_db_operation
    def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Get user settings, create if doesn't exist.

        Args:
            user_id: Telegram user ID

        Returns:
            Dictionary with user settings
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()

        if row:
            settings = dict(row)
        else:
            # Create default settings
            cursor.execute(
                """INSERT INTO user_settings (user_id) VALUES (?)""",
                (user_id,)
            )
            conn.commit()

            cursor.execute(
                "SELECT * FROM user_settings WHERE user_id = ?",
                (user_id,)
            )
            settings = dict(cursor.fetchone())

        conn.close()
        return settings

    @async_db_operation
    def update_user_settings(self, user_id: int, **kwargs) -> bool:
        """Update user settings.

        Args:
            user_id: Telegram user ID
            **kwargs: Settings to update (default_quality, default_format, etc.)

        Returns:
            True if successful
        """
        try:
            # Ensure user exists
            self.get_user_settings.__wrapped__(self, user_id)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build update query
            valid_fields = [
                'default_quality', 'default_format', 'language',
                'auto_delete_after_days', 'notifications_enabled'
            ]
            updates = {k: v for k, v in kwargs.items() if k in valid_fields}

            if not updates:
                conn.close()
                return False

            # Add updated_at timestamp
            updates['updated_at'] = datetime.now().isoformat()

            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [user_id]

            cursor.execute(
                f"UPDATE user_settings SET {set_clause} WHERE user_id = ?",
                values
            )
            conn.commit()
            conn.close()

            logger.info(f"Updated settings for user {user_id}: {updates}")
            return True

        except Exception as e:
            logger.error(f"Failed to update settings for user {user_id}: {e}")
            return False

    @async_db_operation
    def add_download_history(
        self,
        user_id: int,
        url: str,
        platform: str,
        content_type: Optional[str] = None,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        thumbnail_url: Optional[str] = None
    ) -> Optional[int]:
        """Add download to history.

        Args:
            user_id: Telegram user ID
            url: Downloaded URL
            platform: Platform name (instagram, youtube, etc.)
            content_type: Type of content (video, photo, audio, carousel)
            file_path: Path to downloaded file
            file_size: File size in bytes
            title: Content title
            author: Content author
            thumbnail_url: Thumbnail URL

        Returns:
            Download ID if successful, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO download_history
                (user_id, url, platform, content_type, file_path, file_size,
                 title, author, thumbnail_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, url, platform, content_type, file_path, file_size,
                 title, author, thumbnail_url)
            )

            download_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Added download history for user {user_id}: {platform} - {title}")
            return download_id

        except Exception as e:
            logger.error(f"Failed to add download history: {e}")
            return None

    @async_db_operation
    def get_download_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        platform: Optional[str] = None,
        favorites_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get download history for user.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of records
            offset: Offset for pagination
            platform: Filter by platform (optional)
            favorites_only: Show only favorites

        Returns:
            List of download records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM download_history WHERE user_id = ?"
            params = [user_id]

            if platform:
                query += " AND platform = ?"
                params.append(platform)

            if favorites_only:
                query += " AND is_favorite = TRUE"

            query += " ORDER BY download_date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            history = [dict(row) for row in rows]
            conn.close()

            return history

        except Exception as e:
            logger.error(f"Failed to get download history: {e}")
            return []

    @async_db_operation
    def get_download_by_id(self, download_id: int) -> Optional[Dict[str, Any]]:
        """Get specific download by ID.

        Args:
            download_id: Download record ID

        Returns:
            Download record or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM download_history WHERE id = ?",
                (download_id,)
            )
            row = cursor.fetchone()

            result = dict(row) if row else None
            conn.close()

            return result

        except Exception as e:
            logger.error(f"Failed to get download {download_id}: {e}")
            return None

    @async_db_operation
    def add_to_favorites(self, download_id: int) -> bool:
        """Add download to favorites.

        Args:
            download_id: Download record ID

        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE download_history SET is_favorite = TRUE WHERE id = ?",
                (download_id,)
            )

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            return success

        except Exception as e:
            logger.error(f"Failed to add to favorites: {e}")
            return False

    @async_db_operation
    def remove_from_favorites(self, download_id: int) -> bool:
        """Remove download from favorites.

        Args:
            download_id: Download record ID

        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE download_history SET is_favorite = FALSE WHERE id = ?",
                (download_id,)
            )

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            return success

        except Exception as e:
            logger.error(f"Failed to remove from favorites: {e}")
            return False

    @async_db_operation
    def create_collection(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        icon: str = "📁"
    ) -> Optional[int]:
        """Create new collection.

        Args:
            user_id: Telegram user ID
            name: Collection name
            description: Collection description
            icon: Collection icon emoji

        Returns:
            Collection ID if successful, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO collections (user_id, name, description, icon)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, name, description, icon)
            )

            collection_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Created collection '{name}' for user {user_id}")
            return collection_id

        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return None

    @async_db_operation
    def get_collections(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all collections for user.

        Args:
            user_id: Telegram user ID

        Returns:
            List of collections
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM collections WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()

            collections = [dict(row) for row in rows]
            conn.close()

            return collections

        except Exception as e:
            logger.error(f"Failed to get collections: {e}")
            return []

    @async_db_operation
    def add_to_collection(self, download_id: int, collection_id: int) -> bool:
        """Add download to collection.

        Args:
            download_id: Download record ID
            collection_id: Collection ID

        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE download_history SET collection_id = ? WHERE id = ?",
                (collection_id, download_id)
            )

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            return success

        except Exception as e:
            logger.error(f"Failed to add to collection: {e}")
            return False

    @async_db_operation
    def get_collection_items(self, collection_id: int) -> List[Dict[str, Any]]:
        """Get all items in collection.

        Args:
            collection_id: Collection ID

        Returns:
            List of download records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM download_history
                WHERE collection_id = ?
                ORDER BY download_date DESC
                """,
                (collection_id,)
            )
            rows = cursor.fetchall()

            items = [dict(row) for row in rows]
            conn.close()

            return items

        except Exception as e:
            logger.error(f"Failed to get collection items: {e}")
            return []


# Global instance
_db_manager: Optional[DatabaseManager] = None


def init_database(db_path: Path) -> DatabaseManager:
    """Initialize global database manager.

    Args:
        db_path: Path to SQLite database file

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    _db_manager = DatabaseManager(db_path)
    return _db_manager


def get_db_manager() -> Optional[DatabaseManager]:
    """Get the global database manager instance.

    Returns:
        DatabaseManager instance or None if not initialized
    """
    return _db_manager
