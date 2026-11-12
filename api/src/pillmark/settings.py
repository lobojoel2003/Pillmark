"""Runtime configuration, read from environment variables (or a ``.env`` file)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pillmark import __version__


class Settings(BaseSettings):
    """All settings. Variables are prefixed with ``PILLMARK_`` except ``DATABASE_URL``."""

    model_config = SettingsConfigDict(
        env_prefix="PILLMARK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str = Field(
        default="postgresql://pillmark:pillmark@localhost:5432/pillmark",
        validation_alias="DATABASE_URL",
        description="libpq connection string for PostgreSQL.",
    )
    db_pool_min: int = 1
    db_pool_max: int = 10
    migrate_on_start: bool = Field(
        default=False, description="Apply pending database migrations when the API starts."
    )

    cors_origins: list[str] = Field(
        default=["*"],
        description="Origins allowed to call the API from a browser. The API is public.",
    )

    build: str = Field(default="local", description="CI build number, set at image build time.")
    commit: str = Field(default="unknown", description="Git commit SHA, set at image build time.")

    dailymed_base: str = "https://dailymed.nlm.nih.gov/dailymed"
    dailymed_data_base: str = "https://dailymed-data.nlm.nih.gov/public-release-files"
    http_timeout: float = 60.0
    user_agent: str = f"pillmark-importer/{__version__}"

    @property
    def version(self) -> str:
        return __version__


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
