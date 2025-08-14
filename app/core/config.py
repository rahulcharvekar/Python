from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import Field  

class Settings(BaseSettings):
    # Environment-provided
    OPENAI_API_KEY: Optional[str] = None  # loaded from .env or process env
    APP_ENV: str = Field(default="development")

    # Base directory for all storage paths
    BASE_DIR: Path = Path.cwd()

    # File paths (auto-derived unless explicitly overridden in env)
    DB_PATH: Optional[Path] = None
    VECTOR_STORE_DIR: Optional[Path] = None
    UPLOAD_DIR: Optional[Path] = None
    LOG_DIR: Optional[Path] = None

    def model_post_init(self, __context):
        base = Path(self.BASE_DIR)
        self.DB_PATH = Path(self.DB_PATH) if self.DB_PATH else base / "db_store" / "file_registry.db"
        self.VECTOR_STORE_DIR = Path(self.VECTOR_STORE_DIR) if self.VECTOR_STORE_DIR else base / "vector_store"
        self.UPLOAD_DIR = Path(self.UPLOAD_DIR) if self.UPLOAD_DIR else base / "uploads"
        self.LOG_DIR = Path(self.LOG_DIR) if self.LOG_DIR else base / "logs"

    class Config:
        env_file = ".env.local"
        env_file_encoding = "utf-8"

load_dotenv(".env.local")
load_dotenv(".env", override=False)
settings = Settings()
