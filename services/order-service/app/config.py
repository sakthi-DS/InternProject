"""
Configuration settings for Order Service
"""

from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = "postgresql://Sakthivel_P:root@postgres-service:5432/order_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # JWT
    jwt_secret: str = "63346b13fd7c1a8d59e4d584151d42ede8b435079480fab900c1da5b2de63fcc"
    jwt_algorithm: str = "HS256"
    
    # Logging
    log_level: str = "INFO"
    
    # Service URLs
    user_service_url: str = "http://user-service:8001"
    payment_service_url: str = "http://localhost:8003"

    class Config:
        env_file = ".env"


settings = Settings()
