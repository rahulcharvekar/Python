from __future__ import annotations

from langchain_core.tools import tool
from app.services.generic import chat_service


@tool("chat_over_profile")
def chat_over_profile(file: str, query: str) -> str:
    """
    Answer a question grounded in the profile file with strict, file-only retrieval.
    """
    result = chat_service.answer(
        file,
        query,
        k=12,
        score_threshold=0.45,
        strict=True,
    )
    if isinstance(result, dict) and "response" in result:
        return str(result["response"])  # type: ignore[index]
    return str(result)

