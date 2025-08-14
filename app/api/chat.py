# api/upload_file.py

from fastapi import APIRouter, UploadFile, File
import app.workflow.process_chat_query as prcess_chat_query

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{query}")
async def process_query(query):
    print(f"This is the query : {query}")    
    result = prcess_chat_query.initialize(query)
    return {"response": result}
