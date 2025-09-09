# api/upload_file.py

from fastapi import APIRouter, UploadFile, File
from app.agents.agent_factory import build_agent

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{file}/{query}")
async def process_query(file, query):
    # Use the agent to decide and call the appropriate tool
    executor = build_agent("default")
    # Provide structured guidance in natural language
    user_input = (
        f"Use the chat_over_file tool to answer the question using file '{file}'. "
        f"Question: {query}"
    )
    result = executor.invoke({"input": user_input})
    return {"response": result.get("output", result)}
