# api/upload_file.py

from fastapi import APIRouter, UploadFile, File
from app.workflow import process_file  


router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("")
async def upload_file(file: UploadFile = File(...)) -> dict:
    """
    Endpoint to upload a file.
    It saves the file and processes it.
    """
    # Save the uploaded file
    result = await process_file.handle_uploaded_file(file)
    
    return {"response": result}

@router.get("/getall")
async def get_all_files():
    # Save the uploaded file
    result = process_file.get_all_files()
    return result