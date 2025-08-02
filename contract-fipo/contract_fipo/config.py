"""Configuration settings for the contract-fipo application."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # xAI API Configuration
    xai_api_key: str = Field(..., env="XAI_API_KEY")
    xai_base_url: str = Field(default="https://api.x.ai/v1", env="XAI_BASE_URL")
    
    # Database Configuration
    database_url: str = Field(default="postgresql://postgres@localhost/contracts_db", env="DATABASE_URL")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Application Configuration
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()