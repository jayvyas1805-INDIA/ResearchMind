"""
PaperMind — FastAPI application entrypoint.

Phase 1: project skeleton only. No PDF/NLP/embedding/RAG/LLM logic yet —
those are added in later phases.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api import health

settings = get_settings()

# Ensure data/index directories exist so later phases can write to them safely.
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.INDEX_DIR, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    description="NLP & LLM-Powered Research Paper Intelligence Engine",
    version="0.1.0",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health.router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": f"{settings.APP_NAME} API is running",
        "docs": "/docs",
    }
