"""Automatic file cleanup service based on user settings."""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.database.db_manager import get_db_manager
from src.config import config

logger = logging.getLogger(__name__)


class FileCleanupService:
    """Service for cleaning up old downloaded files based on user settings."""

    def __init__(self, cleanup_interval_hours: int = 6):
        """Initialize file cleanup service.

        Args:
            cleanup_interval_hours: How often to run cleanup (default: 6 hours)
        """
        self.cleanup_interval_hours = cleanup_interval_hours
        self.is_running = False
        self.task: Optional[asyncio.Task] = None

        # Statistics
        self.total_files_deleted = 0
        self.total_space_freed_bytes = 0
        self.last_cleanup_time: Optional[datetime] = None
        self.cleanup_runs = 0

    async def start(self) -> None:
        """Start the cleanup service."""
        if self.is_running:
            logger.warning("File cleanup service is already running")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            f"File cleanup service started (interval: {self.cleanup_interval_hours}h)"
        )

    async def stop(self) -> None:
        """Stop the cleanup service."""
        if not self.is_running:
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("File cleanup service stopped")

    async def _cleanup_loop(self) -> None:
        """Main cleanup loop that runs periodically."""
        while self.is_running:
            try:
                await self._run_cleanup()
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _run_cleanup(self) -> None:
        """Run a single cleanup cycle."""
        logger.info("Starting file cleanup cycle")
        self.cleanup_runs += 1

        db = get_db_manager()
        if not db:
            logger.error("Database manager not initialized, skipping cleanup")
            return

        try:
            # Get all users with their settings
            users = await self._get_all_users_with_settings(db)

            files_deleted = 0
            space_freed = 0

            for user_id, settings in users.items():
                auto_delete_days = settings.get('auto_delete_after_days', 0)

                # Skip if auto-delete is disabled (0 means disabled)
                if auto_delete_days <= 0:
                    continue

                # Clean up files for this user
                result = await self._cleanup_user_files(
                    db, user_id, auto_delete_days
                )

                files_deleted += result['files_deleted']
                space_freed += result['space_freed']

            # Update statistics
            self.total_files_deleted += files_deleted
            self.total_space_freed_bytes += space_freed
            self.last_cleanup_time = datetime.now()

            logger.info(
                f"Cleanup cycle completed: {files_deleted} files deleted, "
                f"{space_freed / 1024 / 1024:.2f} MB freed"
            )

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)

    async def _get_all_users_with_settings(
        self, db
    ) -> Dict[int, Dict[str, Any]]:
        """Get all users and their settings.

        Args:
            db: DatabaseManager instance

        Returns:
            Dictionary mapping user_id to settings
        """
        try:
            # Get all user IDs
            user_ids = await db.get_all_user_ids()

            # Get settings for each user
            users = {}
            for user_id in user_ids:
                settings = await db.get_user_settings(user_id)
                users[user_id] = settings

            return users

        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return {}

    async def _cleanup_user_files(
        self, db, user_id: int, auto_delete_days: int
    ) -> Dict[str, int]:
        """Clean up files for a specific user.

        Args:
            db: DatabaseManager instance
            user_id: User ID
            auto_delete_days: Number of days after which to delete files

        Returns:
            Dictionary with 'files_deleted' and 'space_freed' counts
        """
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=auto_delete_days)

            # Get user's download history
            history = await db.get_download_history(user_id, limit=10000)

            files_deleted = 0
            space_freed = 0

            for item in history:
                # Skip if no file path
                if not item.get('file_path'):
                    continue

                # Parse download date
                try:
                    download_date = datetime.fromisoformat(item['download_date'])
                except (ValueError, TypeError):
                    continue

                # Skip if file is newer than cutoff
                if download_date >= cutoff_date:
                    continue

                # Skip if file is in favorites
                if item.get('is_favorite', False):
                    logger.debug(
                        f"Skipping favorite file: {item['file_path']}"
                    )
                    continue

                # Try to delete the file
                file_path = Path(item['file_path'])
                if file_path.exists():
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()

                        files_deleted += 1
                        space_freed += file_size

                        logger.debug(
                            f"Deleted old file for user {user_id}: "
                            f"{file_path.name} ({file_size / 1024:.1f} KB)"
                        )

                    except Exception as e:
                        logger.error(f"Failed to delete file {file_path}: {e}")

            if files_deleted > 0:
                logger.info(
                    f"Cleaned up {files_deleted} files for user {user_id}, "
                    f"freed {space_freed / 1024 / 1024:.2f} MB"
                )

            return {
                'files_deleted': files_deleted,
                'space_freed': space_freed
            }

        except Exception as e:
            logger.error(f"Error cleaning up files for user {user_id}: {e}")
            return {'files_deleted': 0, 'space_freed': 0}

    async def manual_cleanup(
        self, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Manually trigger cleanup for a specific user or all users.

        Args:
            user_id: User ID (None = all users)

        Returns:
            Cleanup statistics
        """
        logger.info(
            f"Manual cleanup triggered for "
            f"{'user ' + str(user_id) if user_id else 'all users'}"
        )

        db = get_db_manager()
        if not db:
            return {'error': 'Database not initialized'}

        try:
            if user_id:
                # Clean up specific user
                settings = await db.get_user_settings(user_id)
                auto_delete_days = settings.get('auto_delete_after_days', 0)

                if auto_delete_days <= 0:
                    return {
                        'error': 'Auto-delete is disabled for this user'
                    }

                result = await self._cleanup_user_files(
                    db, user_id, auto_delete_days
                )

                return {
                    'user_id': user_id,
                    'files_deleted': result['files_deleted'],
                    'space_freed_mb': result['space_freed'] / 1024 / 1024
                }

            else:
                # Clean up all users
                users = await self._get_all_users_with_settings(db)

                total_files = 0
                total_space = 0
                users_cleaned = 0

                for uid, settings in users.items():
                    auto_delete_days = settings.get('auto_delete_after_days', 0)

                    if auto_delete_days <= 0:
                        continue

                    result = await self._cleanup_user_files(
                        db, uid, auto_delete_days
                    )

                    if result['files_deleted'] > 0:
                        users_cleaned += 1
                        total_files += result['files_deleted']
                        total_space += result['space_freed']

                return {
                    'users_cleaned': users_cleaned,
                    'files_deleted': total_files,
                    'space_freed_mb': total_space / 1024 / 1024
                }

        except Exception as e:
            logger.error(f"Error in manual cleanup: {e}")
            return {'error': str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get cleanup service statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'is_running': self.is_running,
            'cleanup_interval_hours': self.cleanup_interval_hours,
            'total_cleanup_runs': self.cleanup_runs,
            'total_files_deleted': self.total_files_deleted,
            'total_space_freed_mb': self.total_space_freed_bytes / 1024 / 1024,
            'last_cleanup_time': (
                self.last_cleanup_time.isoformat()
                if self.last_cleanup_time else None
            )
        }


# Global instance
_cleanup_service: Optional[FileCleanupService] = None


def get_cleanup_service() -> Optional[FileCleanupService]:
    """Get the global cleanup service instance.

    Returns:
        FileCleanupService instance or None
    """
    return _cleanup_service


def init_cleanup_service(cleanup_interval_hours: int = 6) -> FileCleanupService:
    """Initialize the global cleanup service.

    Args:
        cleanup_interval_hours: Cleanup interval in hours

    Returns:
        FileCleanupService instance
    """
    global _cleanup_service
    _cleanup_service = FileCleanupService(cleanup_interval_hours)
    return _cleanup_service
