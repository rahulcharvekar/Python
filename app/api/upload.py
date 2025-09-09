# api/upload_file.py

from fastapi import APIRouter, UploadFile, File
from app.services import file_service


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

@router.get("/getall")
async def get_all_files():
    # List all files
    result = file_service.list_files()
    return result
