"""Application configuration (12-factor, environment-driven).

Single source of truth for configuration, implemented with ``pydantic-settings``.
Field names map case-insensitively to the environment variables documented in
``.env.example`` (e.g. ``database_url`` <- ``DATABASE_URL``). Values are validated
and type-coerced at load time; ``get_settings()`` returns a cached singleton.

Configuration groups (each area is a labelled section below):
    App · Server · Database · Redis · Auth/JWT · Email · Storage · Jobs · Logging · WebSockets
"""

from functools import lru_cache

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants.enums import Environment, LogFormat, StorageBackend


class Settings(BaseSettings):
    """Typed, validated application settings loaded from the environment / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App -----------------------------------------------------------------
    app_name: str = Field(default="HRMS")
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    api_v1_prefix: str = Field(default="/api/v1")
    secret_key: str = Field(default="change-me")

    # --- Server --------------------------------------------------------------
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    allowed_origins: str = Field(default="")
    allowed_hosts: str = Field(default="*")

    # --- Database ------------------------------------------------------------
    database_url: str = Field(default="postgresql+asyncpg://hrms:hrms@localhost:5432/hrms")
    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=20, ge=0)
    db_echo: bool = Field(default=False)
    db_pool_pre_ping: bool = Field(default=True)

    # --- Redis ---------------------------------------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0")
    cache_ttl_seconds: int = Field(default=300, ge=0)

    # --- Auth / JWT ----------------------------------------------------------
    jwt_secret: str = Field(default="change-me")
    jwt_algorithm: str = Field(default="HS256")
    access_token_ttl: int = Field(default=900, ge=1)  # seconds (15 min)
    refresh_token_ttl: int = Field(default=1209600, ge=1)  # seconds (14 days)

    # --- Email / SMTP --------------------------------------------------------
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    email_from: str = Field(default="no-reply@hrms.local")

    # --- File storage / uploads ---------------------------------------------
    storage_backend: StorageBackend = Field(default=StorageBackend.LOCAL)
    upload_dir: str = Field(default="var/uploads")
    max_upload_size_mb: int = Field(default=10, ge=1)

    # --- Background jobs -----------------------------------------------------
    queue_backend: str = Field(default="redis")
    worker_concurrency: int = Field(default=4, ge=1)

    # --- Logging -------------------------------------------------------------
    log_level: str = Field(default="INFO")
    log_format: LogFormat = Field(default=LogFormat.JSON)

    # --- WebSockets ----------------------------------------------------------
    ws_path: str = Field(default="/ws")

    # --- Validators ----------------------------------------------------------
    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        level = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        if level not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}")
        return level

    # --- Derived / computed --------------------------------------------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        """``ALLOWED_ORIGINS`` parsed into a list (comma-separated, trimmed)."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def trusted_hosts(self) -> list[str]:
        """``ALLOWED_HOSTS`` parsed into a list (``*`` allows all)."""
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()] or ["*"]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    @property
    def sync_database_url(self) -> str:
        """The async URL rewritten to a sync driver (used by Alembic / tooling)."""
        return self.database_url.replace("+asyncpg", "+psycopg2")

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()


settings = get_settings()
"""Import-friendly settings singleton: ``from app.core.config.settings import settings``."""
