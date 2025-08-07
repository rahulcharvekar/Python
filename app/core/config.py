from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Base paths
    BASE_DIR: Path = Path.cwd()

    # File paths
    DB_PATH: Path = BASE_DIR / "db_store" / "file_registry.db"
    VECTOR_STORE_DIR: Path = BASE_DIR / "vector_store"
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    LOG_DIR: Path = BASE_DIR / "logs"


    class Config:
        env_file = ".env"  # Tell Pydantic to load this file
        env_file_encoding = "utf-8"


settings = Settings()
