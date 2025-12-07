"""Configuration module - loads settings from .env file."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Application configuration."""

    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not found in .env file")

    # Admin
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "65876198"))

    # App
    APP_NAME: str = os.getenv("APP_NAME", "UspSocDownloader")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    LOGS_DIR: Path = BASE_DIR / "logs"
    DATA_DIR: Path = BASE_DIR / "data"
    TEMP_DIR: Path = DATA_DIR / "temp"

    # Create directories if they don't exist
    LOGS_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)

    # Logging
    LOG_FILE: Path = LOGS_DIR / "bot.log"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Downloader
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB default
    DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", 300))  # 5 min default

    def __repr__(self) -> str:
        """String representation of config."""
        return (
            f"Config(APP_NAME={self.APP_NAME}, DEBUG={self.DEBUG}, "
            f"LOG_LEVEL={self.LOG_LEVEL}, ADMIN_ID={self.ADMIN_ID}, BOT_TOKEN=***)"
        )


# Export config instance
config = Config()
