from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import cloudinary


class Settings(BaseSettings):
    PROJECT_NAME: str = "MiMi PetStore API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"  # Change this in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    # NOTE: Do not hardcode production credentials in source control.
    # Override this via the DATABASE_URL environment variable or a local .env file.
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mimi_petstore"
    
    # CORS
    BACKEND_CORS_ORIGINS: list = [
        "https://3giaydau.io.vn",
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://mimi.thuyluc.shop/"
    ]
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()

# Configure Cloudinary if credentials are provided
if all([
    settings.CLOUDINARY_CLOUD_NAME,
    settings.CLOUDINARY_API_KEY,
    settings.CLOUDINARY_API_SECRET
]):
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET
    )