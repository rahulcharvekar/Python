# api/upload_file.py

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Query
from pathlib import Path
from app.services import file_service
from app.core.config import settings
from app.utils.fileops.fileutils import hash_file
from app.services import insight_services
from app.utils.Logging.logger import logger


router = APIRouter(prefix="/upload", tags=["Upload"])


def _ensure_index(file_name: str) -> None:
    try:
        status = insight_services.check_vector_ready(file_name)
        if isinstance(status, dict) and status.get("ready"):
            logger.info("Vectors already ready for %s", file_name)
            return
        insight_services.create_vector_store(file_name)
        logger.info("Vector store ensured for %s", file_name)
    except Exception as e:
        logger.error("Error ensuring vector store for %s: %s", file_name, e)


@router.post("/simple")
async def simple_upload(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    agent: str | None = Query(default=None, description="Optional agent name to associate this file with"),
) -> dict:
    """
    Simple, UI-friendly upload endpoint. Saves and registers the file, and returns
    structured JSON with status and identifiers.

    Multipart form field name: `file`.
    """
    msg = await file_service.register_upload(file, agent)

    file_path = Path(settings.UPLOAD_DIR) / file.filename
    file_hash = None
    try:
        if file_path.exists():
            file_hash = hash_file(file_path)
    except Exception:
        # Non-fatal: hashing is best-effort for client UX
        file_hash = None

    status = "exists" if "already exists" in (msg or "").lower() else "uploaded"

    # Eager indexing in background to minimize first-chat latency and repeated vectorization
    try:
        if background_tasks is not None:
            background_tasks.add_task(_ensure_index, file.filename)
        else:
            # Fallback: run inline if BackgroundTasks not provided (should not block much if already ready)
            _ensure_index(file.filename)
    except Exception as e:
        logger.warning("Failed to schedule eager indexing for %s: %s", file.filename, e)
    return {
        "file_name": file.filename,
        "file_hash": file_hash,
        "status": status,
        "message": msg,
    }

