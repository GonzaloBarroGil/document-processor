from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and ``.env``."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://docproc:docproc@postgres:5432/docproc"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "documents"
    minio_secure: bool = False

    ocr_primary_engine: str = "paddle"
    ocr_fallback_engine: str = "easyocr"
    ocr_timeout_seconds: int = 60
    ocr_confidence_threshold: float = 0.7

    max_image_size_bytes: int = 10 * 1024 * 1024
    allowed_media_types: list[str] = [
        "image/jpeg",
        "image/png",
        "image/heic",
        "application/pdf",
    ]

    rate_limit_per_minute: int = 60
    rate_limit_window_seconds: int = 60

    storage_high_watermark_pct: float = 85.0
    storage_critical_pct: float = 95.0
    storage_alert_ack_window_hours: int = 72
    storage_critical_window_hours: int = 24
    storage_lifecycle_run_interval_minutes: int = 360
    storage_expire_completed_days: int = 90
    storage_expire_critical_days: int = 30

    worker_poll_interval_seconds: float = 1.0
    worker_visibility_timeout_seconds: int = 300
    worker_max_retries: int = 3

    jwt_secret: str = Field(
        default="dev-only-jwt-secret-please-change-me-in-production",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 15 * 60
    refresh_token_ttl_seconds: int = 7 * 24 * 60 * 60

    log_level: str = "INFO"


settings = Settings()
