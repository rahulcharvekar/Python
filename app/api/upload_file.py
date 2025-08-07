# api/upload_file.py

from fastapi import APIRouter, UploadFile, File
import os
from app.workflow import process_file  
from app.core.config import settings
from app.utils.Logging.logger import logger

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    logger.info(f"Received file: {file.filename}")
    file_location = os.path.join(settings.UPLOAD_DIR, file.filename)
    
    with open(file_location, "wb") as f:
        content = await file.read()
        f.write(content)

    result = process_file.handle_uploaded_file(file_location)
    print(result)
    return {"response": result}
