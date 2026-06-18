"""
FastAPI application entry point.
Handles lifespan: DB migration, model warm-up, and service initialization.
"""
import contextlib
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger

settings = get_settings()
setup_logging("DEBUG" if settings.DEBUG else "INFO")
logger = get_logger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Starting up Real-Time AI Privacy Display API")

    # 1. Database initialization/migrations
    if settings.DATABASE_URL.startswith("sqlite"):
        try:
            db_url_parts = settings.DATABASE_URL.split(":///")
            if len(db_url_parts) > 1:
                db_path = db_url_parts[1]
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
            
            from app.db.session import engine, Base
            import app.db.models
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("SQLite database tables created/verified")
        except Exception as e:
            logger.error("SQLite auto-creation failed", extra={"error": str(e)})
    elif settings.DATABASE_PROVIDER != "firestore":
        try:
            import subprocess
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True, text=True, cwd=backend_dir
            )
            if result.returncode != 0:
                logger.warning("Alembic migration warning", extra={"stderr": result.stderr})
            else:
                logger.info("Database migrations applied")
        except Exception as e:
            logger.error("Migration failed", extra={"error": str(e)})

    # 1.5 Check and download local AI models if missing from AppData
    try:
        from app.services.model_manager import check_models, download_models
        if not check_models():
            logger.info("Local models missing. Downloading to AppData folder...")
            download_models()
        else:
            logger.info("Local models verified in AppData folder.")
    except Exception as e:
        logger.error("Failed to check/download local models", extra={"error": str(e)})

    # 2. Initialize FAISS vector store
    from app.services.vector_store import init_vector_store
    init_vector_store(settings.FAISS_INDEX_PATH, settings.EMBEDDING_DIM)
    logger.info("Vector store initialized", extra={"path": settings.FAISS_INDEX_PATH})

    # 3. Load Sentence Transformer (most expensive — warm up before serving)
    from app.services.embedder import init_embedder
    init_embedder(settings.EMBEDDING_MODEL)
    logger.info("Embedding model loaded", extra={"model": settings.EMBEDDING_MODEL})

    # 4. Initialize Gemini
    if settings.GEMINI_API_KEY:
        from app.services.gemini_service import init_gemini
        init_gemini(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
        logger.info("Gemini service initialized", extra={"model": settings.GEMINI_MODEL})
    else:
        logger.warning("GEMINI_API_KEY not set — Gemini service will fail at runtime")

    # 5. Load Whisper STT model
    from app.services.stt_service import init_stt
    init_stt(settings.WHISPER_MODEL_SIZE, settings.WHISPER_DEVICE, settings.WHISPER_COMPUTE_TYPE)
    logger.info("Whisper STT model loaded", extra={"size": settings.WHISPER_MODEL_SIZE})

    logger.info("All services initialized — ready to serve")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security Hardening Headers Middleware ──────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response

# ── Rate Limiting ─────────────────────────────────────────────────────────────
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from fastapi.responses import JSONResponse
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )

# ── Routers ───────────────────────────────────────────────────────────────────
from app.api.profile import router as profile_router
from app.api.resume import router as resume_router
from app.api.projects import router as projects_router
from app.api.skills import router as skills_router
from app.api.interview import router as interview_router
from app.api.audio import router as audio_router
from app.api.realtime_ws import router as realtime_ws_router

app.include_router(profile_router, prefix="/api")
app.include_router(resume_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(skills_router, prefix="/api")
app.include_router(interview_router, prefix="/api")
app.include_router(audio_router, prefix="/api")
app.include_router(realtime_ws_router, prefix="/api")


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
