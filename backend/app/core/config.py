from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

import sys
import os

def get_env_path():
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, ".env")
    return ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_path(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "Real-Time AI Privacy Display"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/reai.db"
    DATABASE_PROVIDER: str = "sqlite"  # 'sqlite', 'firestore', or 'supabase'
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None

    # ── Auth ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-256-bit-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False  # Set dynamically in model_validator if not explicitly provided
    FIREBASE_SERVICE_ACCOUNT_JSON: str | None = None
    FIREBASE_WEB_API_KEY: str | None = None

    # ── Gemini ────────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── Whisper ───────────────────────────────────────────────────────────────
    WHISPER_MODEL_SIZE: str = "base"   # tiny | base | small | medium
    WHISPER_DEVICE: str = "cpu"        # cpu | cuda
    WHISPER_COMPUTE_TYPE: str = "int8"

    # ── Embeddings ────────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # ── FAISS ─────────────────────────────────────────────────────────────────
    FAISS_INDEX_PATH: str = "./data/faiss_indices"
    MODEL_DIR: str = ""

    # ── RAG ───────────────────────────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = 5
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64

    # ── File Upload ───────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_MIME_TYPES: list[str] = ["application/pdf"]

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Encryption ────────────────────────────────────────────────────────────
    ENCRYPTION_KEY: str = "change-me-to-a-valid-fernet-key-32-bytes-b64="

    # ── Observability ─────────────────────────────────────────────────────────
    SENTRY_DSN: str | None = None

    # ── OpenAI ────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str | None = None

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://modi-krish.github.io",
        "app://.",
        "file://"
    ]

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "Settings":
        import os
        import sys

        if self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError("CHUNK_OVERLAP must be less than CHUNK_SIZE to prevent infinite loops during chunking.")
        # If COOKIE_SECURE is not explicitly set, default to True in production (not DEBUG)
        if "COOKIE_SECURE" not in self.model_fields_set:
            self.COOKIE_SECURE = not self.DEBUG
        
        # Determine base user directory
        is_frozen = getattr(sys, "frozen", False)
        appdata = os.getenv("APPDATA")
        if not appdata:
            appdata = os.path.expanduser("~/Library/Application Support" if sys.platform == "darwin" else "~/.local/share")
            
        reai_user_dir = os.path.join(appdata, "REAI")
        
        # Dynamic paths when packaged/frozen
        if is_frozen:
            # Re-route database path to writeable AppData folder
            if self.DATABASE_URL.startswith("sqlite+aiosqlite:///./data"):
                db_dir = os.path.join(reai_user_dir, "data")
                self.DATABASE_URL = f"sqlite+aiosqlite:///{db_dir}/reai.db"
            
            # Re-route FAISS index path to writeable AppData folder
            if self.FAISS_INDEX_PATH == "./data/faiss_indices":
                self.FAISS_INDEX_PATH = os.path.join(reai_user_dir, "faiss_indices")
                
            # Resolve Firebase Service Account JSON relative to PyInstaller _internal dir
            if self.FIREBASE_SERVICE_ACCOUNT_JSON and not os.path.isabs(self.FIREBASE_SERVICE_ACCOUNT_JSON):
                self.FIREBASE_SERVICE_ACCOUNT_JSON = os.path.join(sys._MEIPASS, self.FIREBASE_SERVICE_ACCOUNT_JSON)

        # Determine AppData model directory
        if not self.MODEL_DIR:
            self.MODEL_DIR = os.path.join(reai_user_dir, "models")
            
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
