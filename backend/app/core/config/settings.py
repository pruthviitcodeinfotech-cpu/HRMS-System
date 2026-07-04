"""Application configuration (12-factor, environment-driven).

Foundation phase: this is the single source of truth for configuration. The
concrete Pydantic ``Settings`` class is filled in during implementation; the
groups below document every configuration area the application will read from
the environment. See ``.env.example`` for the corresponding keys.

Configuration groups (to be implemented with pydantic-settings BaseSettings):

    App:        APP_NAME, ENVIRONMENT, DEBUG, API_V1_PREFIX, SECRET_KEY
    Server:     HOST, PORT, ALLOWED_ORIGINS
    Database:   DATABASE_URL (async), DB_POOL_SIZE, DB_MAX_OVERFLOW
    Redis:      REDIS_URL, CACHE_TTL_SECONDS
    Auth/JWT:   JWT_ALGORITHM, ACCESS_TOKEN_TTL, REFRESH_TOKEN_TTL, JWT_SECRET
    Email:      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM
    Storage:    STORAGE_BACKEND, UPLOAD_DIR, MAX_UPLOAD_SIZE_MB
    Jobs:       QUEUE_BACKEND, WORKER_CONCURRENCY
    Logging:    LOG_LEVEL, LOG_FORMAT
    WebSockets: WS_PATH

Usage (implementation phase):

    from functools import lru_cache

    @lru_cache
    def get_settings() -> "Settings":
        return Settings()
"""

# class Settings(BaseSettings):
#     ...  # defined in implementation phase
#
# def get_settings() -> "Settings":
#     ...
