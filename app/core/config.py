# core/config.py
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import Field

class Settings(BaseSettings):
    # === Environment selection ===
    APP_ENV: str = Field(default="development")  # "development" | "production"

    # === OpenAI (prod) ===
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = Field(default="gpt-4.1")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")

    # === Local LLM (dev) — OpenAI-compatible server like Ollama ===
    # Ollama default shim: http://127.0.0.1:11434/v1  (ollama serve)
    LOCAL_LLM_MODEL: str = Field(default="llama3.1:8b-instruct")
    LOCAL_LLM_BASE_URL: str = Field(default="http://127.0.0.1:11434/v1")
    LOCAL_LLM_API_KEY: str = Field(default="ollama")  # dummy; Ollama ignores it
    HUGGINGFACE_EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")

    # === Storage roots ===
    # Set BASE_DIR via env (e.g., BASE_DIR=/mnt/storage). Defaults to /mnt/storage in prod-like
    # environments; override locally as needed.
    BASE_DIR: Path = Path("/mnt/storage")

    # Optional overrides via env; otherwise derived from BASE_DIR
    VECTOR_STORE_DIR: Optional[Path] = None
    UPLOAD_DIR: Optional[Path] = None
    LOG_DIR: Optional[Path] = None
    DB_DIR: Optional[Path] = None

    def model_post_init(self, __context):
        base = Path(self.BASE_DIR)

        # Derive default paths if not set        
        self.VECTOR_STORE_DIR = Path(self.VECTOR_STORE_DIR) if self.VECTOR_STORE_DIR else base / "vector_store"
        self.UPLOAD_DIR = Path(self.UPLOAD_DIR) if self.UPLOAD_DIR else base / "uploads"
        self.LOG_DIR = Path(self.LOG_DIR) if self.LOG_DIR else base / "logs"
        # DB_DIR now derived under BASE_DIR by default (e.g., /mnt/storage/db_store)
        self.DB_DIR = Path(self.DB_DIR) if self.DB_DIR else base / "db_store"

        # Create folders if they don't exist
        for p in [self.VECTOR_STORE_DIR, self.UPLOAD_DIR, self.LOG_DIR, self.DB_DIR]:
            p.mkdir(parents=True, exist_ok=True)


    class Config:
        env_file = ".env.local"   # primary
        env_file_encoding = "utf-8"

# Load .env files (local first, then .env without overriding existing keys)
load_dotenv(".env.local")
load_dotenv(".env", override=False)

settings = Settings()
