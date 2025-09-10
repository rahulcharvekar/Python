# api/upload_file.py

from fastapi import APIRouter, UploadFile, File
from pathlib import Path
from app.services import file_service
from app.core.config import settings
from app.utils.fileops.fileutils import hash_file


router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("")
async def upload_file(file: UploadFile = File(...)) -> dict:
    """
    Endpoint to upload a file.
    It saves the file and processes it.
    """
    # Save the uploaded file
    result = await file_service.register_upload(file)
    
    return {"response": result}


@router.post("/simple")
async def simple_upload(file: UploadFile = File(...)) -> dict:
    """
    Simple, UI-friendly upload endpoint. Saves and registers the file, and returns
    structured JSON with status and identifiers.

    Multipart form field name: `file`.
    """
    msg = await file_service.register_upload(file)

    file_path = Path(settings.UPLOAD_DIR) / file.filename
    file_hash = None
    try:
        if file_path.exists():
            file_hash = hash_file(file_path)
    except Exception:
        # Non-fatal: hashing is best-effort for client UX
        file_hash = None

    status = "exists" if "already exists" in (msg or "").lower() else "uploaded"
    return {
        "file_name": file.filename,
        "file_hash": file_hash,
        "status": status,
        "message": msg,
    }

@router.get("/getall")
async def get_all_files():
    # List all files
    result = file_service.list_files()
    return result
