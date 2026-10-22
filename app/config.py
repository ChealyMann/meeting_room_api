from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str = Field(min_length=32)
    access_token_minutes: int = Field(default=15, ge=1)
    refresh_token_days: int = Field(default=7, ge=1)
    upload_dir: Path = Path("./uploads")
    max_upload_mb: int = Field(default=5, ge=1)
    max_photos_per_room: int = Field(default=20, ge=1)
    cors_origins: str = ""

    # Used only by scripts/seed.py.
    first_admin_email: str | None = None
    first_admin_password: str | None = None
    first_admin_staff_id: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
