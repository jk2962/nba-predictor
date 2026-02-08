"""
NBA Player Performance Prediction - Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "sqlite:///./data/nba.db"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Cache
    cache_ttl: int = 300  # 5 minutes
    
    # Model paths
    models_dir: str = "models"
    
    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
