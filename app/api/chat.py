# api/upload_file.py

from fastapi import APIRouter, UploadFile, File
from app.agents.agent_factory import build_agent
from app.services import chat_service

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


@router.post("/{query}")
async def plain_chat(query: str):
    """
    Plain chat without file context. For file-contextual chat, use /chat/{file}/{query}.
    """
    result = chat_service.plain_chat(query)
    # chat_service.plain_chat returns a dict with key "response"
    return {"response": result.get("response", result)}
