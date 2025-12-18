from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Vendor Financial Assessment"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database - SQLite by default (no setup required)
    DATABASE_URL: str = "sqlite:///./vfa.db"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"  # Fast model for extraction
    OPENAI_VISION_MODEL: str = "gpt-4o"

    # File Upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: list = ["application/pdf"]
    UPLOAD_DIR: str = "uploads"

    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
