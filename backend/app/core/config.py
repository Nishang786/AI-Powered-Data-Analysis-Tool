from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "DS Platform (Gemini)"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:8501"]

    # Storage
    UPLOAD_DIR: str = "app/storage/uploads"
    PROCESSED_DIR: str = "app/storage/processed"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100 MB

    # Gemini - read API key from environment variable named GEMINI_API_KEY or from .env
    # NOTE: previously this used a literal API key string as the env var name which prevented
    # the application from reading the actual key. Keep your real key in an environment
    # variable or in a .env file (not checked into source control).
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEFAULT_GEMINI_MODEL: str = "gemini-2.5-flash"
    DEFAULT_TEMPERATURE: float = 0.3
    DEFAULT_MAX_TOKENS: int = 1500
    DEBUG: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
