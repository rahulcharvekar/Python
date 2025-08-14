# api/upload_file.py

from fastapi import APIRouter, UploadFile, File
import app.workflow.get_insights as get_insights

router = APIRouter(prefix="/get_insights", tags=["get_insights"])


@router.post("/{file}")
async def initialize_ai(file):
    print(f"This is the : {file}")    
    result = get_insights.initialize(file)
    return {"response": result}
