from typing import List

from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Bot settings
    BOT_TOKEN: SecretStr
    ADMIN_USER_IDS: List[int] = []

    # Database settings
    DATABASE_URL: PostgresDsn

    # WebApp settings
    WEBAPP_URL: str
    WEBAPP_HOST: str = "0.0.0.0"
    WEBAPP_PORT: int = 8000

    # APScheduler settings
    SCHEDULER_TIMEZONE: str = "UTC"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


# Create settings instance for import
settings = Settings()
