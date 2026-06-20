# ruff: noqa: E402
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

if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastAPIIntegration
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0 if settings.DEBUG else 0.1,
        profiles_sample_rate=1.0 if settings.DEBUG else 0.1,
        integrations=[FastAPIIntegration()]
    )

setup_logging("DEBUG" if settings.DEBUG else "INFO")
logger = get_logger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Starting up Real-Time AI Privacy Display API")

    # Production Secret Validation Gating
    if not settings.DEBUG:
        if settings.SECRET_KEY == "change-me-in-production-use-256-bit-random-string" or len(settings.SECRET_KEY) < 16:
            logger.critical("Insecure SECRET_KEY configured in production mode!")
            raise RuntimeError("Production startup failed: Insecure SECRET_KEY configuration.")
        
        if settings.ENCRYPTION_KEY == "change-me-to-a-valid-fernet-key-32-bytes-b64=":
            logger.critical("Default ENCRYPTION_KEY configured in production mode!")
            raise RuntimeError("Production startup failed: Insecure ENCRYPTION_KEY configuration.")
            
        from app.services.firebase_admin_service import _initialized as fb_initialized
        if not fb_initialized:
            logger.critical("Firebase Admin is not initialized! Firebase authentication will fail in production.")
            raise RuntimeError("Production startup failed: Firebase Admin configuration missing.")

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

    # 1.6 Initialize Firebase Admin (Required for Auth)
    if settings.FIREBASE_SERVICE_ACCOUNT_JSON and os.path.exists(settings.FIREBASE_SERVICE_ACCOUNT_JSON):
        import firebase_admin
        from firebase_admin import credentials
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin initialized for Auth")
        except Exception as e:
            logger.error("Failed to initialize Firebase Admin", extra={"error": str(e)})
    else:
        logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON not found. Firebase Auth will fail.")

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

# Prometheus Metrics
from prometheus_client import make_asgi_app
app.mount("/metrics", make_asgi_app())

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
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router

app.include_router(auth_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(resume_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(skills_router, prefix="/api")
app.include_router(interview_router, prefix="/api")
app.include_router(audio_router, prefix="/api")
app.include_router(realtime_ws_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


# ── Health Check ──────────────────────────────────────────────────────────────
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

@app.get("/health/live", tags=["health"])
@app.get("/health", tags=["health"])
async def health_live():
    return {"status": "ok", "version": settings.APP_VERSION}

@app.get("/health/ready", tags=["health"])
async def health_ready(db: AsyncSession = Depends(get_db)):
    from app.core.redis import ping_redis
    from app.services.stt_service import get_stt
    
    postgres_ok = False
    redis_ok = False
    openai_ok = False
    supabase_ok = False
    
    # 1. Test PostgreSQL
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception as e:
        logger.error("Health check: PostgreSQL failed", extra={"error": str(e)})

    # 2. Test Redis
    try:
        redis_ok = await ping_redis()
    except Exception as e:
        logger.error("Health check: Redis failed", extra={"error": str(e)})

    # 3. Test OpenAI API connection
    try:
        stt = get_stt()
        client = stt.get_client()
        await client.models.list()
        openai_ok = True
    except Exception as e:
        logger.error("Health check: OpenAI API failed", extra={"error": str(e)})

    # 4. Test Supabase config
    try:
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            supabase_ok = True
    except Exception:
        pass

    status_code = 200
    if not (postgres_ok and redis_ok and openai_ok and supabase_ok):
        status_code = 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if status_code == 200 else "unready",
            "components": {
                "postgres": "ok" if postgres_ok else "failed",
                "redis": "ok" if redis_ok else "failed",
                "openai": "ok" if openai_ok else "failed",
                "supabase": "ok" if supabase_ok else "failed",
            }
        }
    )
