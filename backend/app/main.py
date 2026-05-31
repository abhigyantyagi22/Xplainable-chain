from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import logging
import uvicorn

from app.routers import analyze, verify, audit, causal, causal_novel, causal_api, prevent, blockchain_data
from app.routers import admin, metrics, feedback
from app.utils.config import settings
from app.middleware.auth import verify_api_key, init_key_store
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.telemetry import TelemetryMiddleware
from app.utils.secrets import run_security_checks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-30s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Rate limit config ──────────────────────────────────────────────────────────
# (max_calls, window_seconds) per route prefix
_ROUTE_LIMITS = {
    "/api/analyze/causal": (5,  60),   # causal inference is expensive
    "/api/analyze":        (10, 60),   # ML inference + SHAP
    "/api/check-before-send": (20, 60),
    "/api/quick-address-check": (60, 60),
    "/api/audit":          (30, 60),
    "/api/verify":         (30, 60),
}
_DEFAULT_LIMIT = (60, 60)   # 60 req/min for everything else


# ── App lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────────
    logger.info("XAI-Chain API starting up…")

    # Security audit (prints warnings for insecure configs)
    run_security_checks()

    # Initialise MongoDB — shared by auth key store + telemetry
    try:
        mongo_client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=3000)
        db = mongo_client.get_database()
        init_key_store(db["api_keys"])
        # Store DB reference on app state so TelemetryMiddleware can pick it up
        app.state.mongo_db = db
        logger.info("MongoDB connected and ready")
    except Exception as e:
        app.state.mongo_db = None
        logger.warning(f"MongoDB unavailable at startup: {e}. Auth falls back to MASTER_API_KEY only.")

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info("XAI-Chain API shutting down.")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="XAI-Chain API",
    description="Explainable AI for Blockchain Security",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — keep before rate limiting so pre-flight OPTIONS requests are handled first
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://xai-chain.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting — after CORS, before auth
app.add_middleware(
    RateLimitMiddleware,
    route_limits=_ROUTE_LIMITS,
    default_limit=_DEFAULT_LIMIT,
)

# Telemetry — innermost middleware so it measures actual handler latency
# Collection is None at init time; wired up in lifespan after MongoDB connects
app.add_middleware(TelemetryMiddleware, collection=None)

# ── Routers ────────────────────────────────────────────────────────────────────

# Public — no auth required (health, docs are served by FastAPI automatically)
app.include_router(admin.router)  # admin uses its own require_master_key dep

# Protected — all require a valid API key
_auth = [Depends(verify_api_key)]

app.include_router(prevent.router,       tags=["prevention"],  dependencies=_auth)
app.include_router(analyze.router,       prefix="/api/analyze", tags=["analyze"],  dependencies=_auth)
app.include_router(verify.router,        prefix="/api/verify",  tags=["verify"],   dependencies=_auth)
app.include_router(audit.router,         prefix="/api/audit",   tags=["audit"],    dependencies=_auth)
app.include_router(causal.router,        tags=["causal-analysis"], dependencies=_auth)
app.include_router(causal_novel.router,  dependencies=_auth)
app.include_router(causal_api.router,    dependencies=_auth)
app.include_router(blockchain_data.router, tags=["blockchain"], dependencies=_auth)
app.include_router(metrics.router)    # auth handled per-endpoint inside metrics.py
app.include_router(feedback.router, dependencies=_auth)


# ── Public utility endpoints ───────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "XAI-Chain API",
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs",
        "auth": "Include X-API-Key header on all /api/* requests",
    }


@app.get("/health", include_in_schema=False)
def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
