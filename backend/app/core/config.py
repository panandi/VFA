import os
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()


class Settings(BaseModel):
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
    ALLOWED_FILE_TYPES: List[str] = ["application/pdf"]
    UPLOAD_DIR: str = "uploads"

    # CORS - Allow all localhost ports for development
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]


def _load_settings() -> Settings:
    """Load settings from environment variables."""
    return Settings(
        APP_NAME=os.getenv("APP_NAME", "Vendor Financial Assessment"),
        APP_VERSION=os.getenv("APP_VERSION", "1.0.0"),
        DEBUG=os.getenv("DEBUG", "false").lower() == "true",
        DATABASE_URL=os.getenv("DATABASE_URL", "sqlite:///./vfa.db"),
        SECRET_KEY=os.getenv("SECRET_KEY", "your-secret-key-change-in-production"),
        ALGORITHM=os.getenv("ALGORITHM", "HS256"),
        ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        OPENAI_VISION_MODEL=os.getenv("OPENAI_VISION_MODEL", "gpt-4o"),
        MAX_FILE_SIZE_MB=int(os.getenv("MAX_FILE_SIZE_MB", "50")),
        UPLOAD_DIR=os.getenv("UPLOAD_DIR", "uploads"),
    )


settings = _load_settings()
