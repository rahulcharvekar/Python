# api/upload_file.py

from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from pathlib import Path
from app.services.generic import upload_service
from app.core.config import settings
from app.utils.fileops.fileutils import hash_file
from app.services.generic import insight_services, ingestion_db
from app.services.agents import dochelp_service
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


def _ensure_index_and_update_db(agent: str | None, file_name: str) -> None:
    """
    Ensure vectors for the file and persist the vector collection name in SQLite for the given agent.
    Preserves existing title/tags if a row already exists.
    """
    try:
        status = insight_services.check_vector_ready(file_name)
        if not (isinstance(status, dict) and status.get("ready")):
            insight_services.create_vector_store(file_name)
            status = insight_services.check_vector_ready(file_name)

        collection = status.get("collection") if isinstance(status, dict) else None
        if not agent:
            return

        # Preserve existing fields when updating
        try:
            rows = ingestion_db.list_documents(agent)
            row = next((r for r in rows if isinstance(r, dict) and r.get("file") == file_name), None)
        except Exception:
            row = None

        title = (row or {}).get("title") if isinstance(row, dict) else None
        keywords = (row or {}).get("keywords") if isinstance(row, dict) else None

        ingestion_db.upsert_document(
            agent=agent,
            file=file_name,
            title=title,
            vector_collection=str(collection or ""),
            keywords=keywords,
        )
    except Exception as e:
        logger.error("Error ensuring updating db %s: %s", file_name, e)
    


def _index_and_enrich(agent: str, file_name: str) -> None:
    """Ensure vectors, persist collection in DB, then enrich metadata per agent."""
    agent_name = (agent or "").strip().lower()
    if not agent_name:
        return
    try:
        _ensure_index_and_update_db(agent_name, file_name)
    except Exception:
        # Continue to enrichment even if index update had issues (best-effort)
        pass

    dochelp_service.ingest_document(file_name, agent=agent_name)


@router.post("/{agent}")
async def upload_for_agent(
    agent: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
) -> dict:
    """
    Upload endpoint scoped to a specific agent. Saves and registers the file, then
    returns structured JSON with status and identifiers.

    Multipart form field name: `file`.
    """
    # Save the file directly via upload_service
    # Check if the file already exists for idempotent UX
    target_path = Path(settings.UPLOAD_DIR) / file.filename
    existed = target_path.exists()
    await upload_service.upload_file(file)
    if existed:
        msg = f"File \"{file.filename}\" already exists; you can chat over it right away."
    else:
        msg = f"File '{file.filename}' uploaded successfully."

    file_path = Path(settings.UPLOAD_DIR) / file.filename
    file_hash = None
    try:
        if file_path.exists():
            file_hash = hash_file(file_path)
    except Exception:
        # Non-fatal: hashing is best-effort for client UX
        file_hash = None

    status = "exists" if existed else "uploaded"

    # Eager indexing in background to minimize first-chat latency and repeated vectorization
    try:
        if background_tasks is not None:
            background_tasks.add_task(_index_and_enrich, agent, file.filename)
        else:
            # Fallback: run inline if BackgroundTasks not provided
            _index_and_enrich(agent, file.filename)
    except Exception as e:
        logger.warning("Failed to schedule eager indexing for %s: %s", file.filename, e)
    return {
        "file_name": file.filename,
        "file_hash": file_hash,
        "status": status,
        "message": msg,
    }
