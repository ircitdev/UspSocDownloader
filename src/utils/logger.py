"""Logger configuration module."""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional


class Logger:
    """Logger configuration and management."""

    _instance: Optional[logging.Logger] = None
    _initialized: bool = False

    @classmethod
    def get_logger(cls, name: str = "bot") -> logging.Logger:
        """Get or create logger instance.

        Args:
            name: Logger name, defaults to 'bot'

        Returns:
            Configured logger instance
        """
        if cls._instance is not None:
            return cls._instance

        logger = logging.getLogger(name)

        if not cls._initialized:
            cls._setup_logger(logger)
            cls._initialized = True
            cls._instance = logger

        return logger

    @staticmethod
    def _setup_logger(logger: logging.Logger) -> None:
        """Setup logger configuration.

        Args:
            logger: Logger instance to configure
        """
        from src.config import config

        # Set log level
        logger.setLevel(getattr(logging, config.LOG_LEVEL))

        # Create formatters
        formatter = logging.Formatter(config.LOG_FORMAT)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            filename=config.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,  # Keep 5 backup files
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.debug(f"Logger initialized - {config}")


# Export logger function
get_logger = Logger.get_logger
