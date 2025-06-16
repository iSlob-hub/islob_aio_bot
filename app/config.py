from typing import List, Optional

from pydantic import SecretStr, MongoDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Bot settings
    BOT_TOKEN: str

    # APScheduler settings
    SCHEDULER_TIMEZONE: str = "UTC"

    # MongoDB settings
    # Connection details
    MONGODB_HOST: str = "mongodb"
    MONGODB_PORT: int = 27017
    MONGODB_USER: Optional[str] = None
    MONGODB_PASSWORD: Optional[str] = None

    # Database name
    MONGODB_DB_NAME: str = "my_app_db"

    # Connection options
    MONGODB_MAX_POOL_SIZE: int = 100
    MONGODB_MIN_POOL_SIZE: int = 10
    MONGODB_MAX_IDLE_TIME_MS: int = 10000

    # Generate MongoDB connection string
    @property
    def mongodb_connection_string(self) -> str:
        """Generate the MongoDB connection string based on settings"""
        credentials = ""
        if self.MONGODB_USER and self.MONGODB_PASSWORD:
            credentials = f"{self.MONGODB_USER}:{self.MONGODB_PASSWORD}"

        return f"mongodb://{credentials}@{self.MONGODB_HOST}:{self.MONGODB_PORT}/{self.MONGODB_DB_NAME}?authSource=admin"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


# Create settings instance for import
settings = Settings()
