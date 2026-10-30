"""Read-only settings endpoint — exposes non-secret config for the Settings page."""
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("")
def get_public_settings():
    s = get_settings()
    return {
        "app_name": s.APP_NAME,
        "environment": s.ENVIRONMENT,
        "embedding_model": s.EMBEDDING_MODEL,
        "chunk_target_words": s.CHUNK_TARGET_WORDS,
        "default_top_k": s.DEFAULT_TOP_K,
        "min_similarity_threshold": s.MIN_SIMILARITY_THRESHOLD,
        "llm_provider": s.LLM_PROVIDER,
        "llm_model": s.LLM_MODEL,
        "max_upload_size_mb": s.MAX_UPLOAD_SIZE_MB,
    }
