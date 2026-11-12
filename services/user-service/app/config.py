
"""
Configuration settings for User Service
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Database
    db_host: str = Field(
        default="postgres-service",
        validation_alias="DATABASE_HOST"
    )

    db_port: int = Field(
        default=5432,
        validation_alias="DATABASE_PORT"
    )

    db_name: str = Field(
        default="user_db",
        validation_alias="DATABASE_NAME"
    )

    db_user: str = Field(
        default="",
        validation_alias="DATABASE_USER"
    )

    db_password: str = Field(
        default="",
        validation_alias="DATABASE_PASSWORD"
    )

    @property
    def database_url(self):
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    jwt_secret: str = "63346b13fd7c1a8d59e4d584151d42ede8b435079480fab900c1da5b2de63fcc"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Logging
    log_level: str = "INFO"

    # Service URLs
    order_service_url: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
