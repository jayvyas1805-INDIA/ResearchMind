"""
PaperMind — FastAPI application entrypoint.
"""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import init_db
from app.api import chat, comparison, health, leaderboard, papers, search, settings as settings_api, summary

settings = get_settings()

# --- Logging: one place for the whole app, level depends on ENVIRONMENT ---
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("papermind")

# Ensure data/index directories exist so later phases can write to them safely.
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.INDEX_DIR, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    description="NLP & LLM-Powered Research Paper Intelligence Engine",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("%s started (env=%s)", settings.APP_NAME, settings.ENVIRONMENT)


# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Global exception handler: never leak internals, always log server-side ---
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


# --- Routers ---
app.include_router(health.router, prefix="/api")
app.include_router(papers.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(comparison.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(leaderboard.router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": f"{settings.APP_NAME} API is running",
        "docs": "/docs",
    }
