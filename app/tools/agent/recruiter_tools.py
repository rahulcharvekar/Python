from __future__ import annotations

import json
from langchain_core.tools import tool

from app.services.agents import recruiter_service
from app.services.generic import chat_service


@tool("translate_job_description")
def translate_job_description(description: str) -> str:
    """Translate the job description into English when needed."""
    text, translated = recruiter_service.translate_description(description)
    payload = {"text": text, "translated": bool(translated)}
    return json.dumps(payload)


@tool("search_recruiter_candidates")
def search_recruiter_candidates(description: str, max_results: int = 5) -> str:
    """Return the strongest candidate matches for the provided description."""
    matches = recruiter_service.search_candidates(description, max_results=max_results)
    payload = {
        "matches": [match.as_dict() for match in matches],
        "count": len(matches),
    }
    return json.dumps(payload)


@tool("chat_over_profile")
def chat_over_profile(
    file: str,
    query: str,
    k: int = 24,
    score_threshold: float = 0.45,
    strict: bool = False,
) -> str:
    """Answer a resume-specific question for the recruiter agent."""
    result = chat_service.answer(
        file,
        query,
        k=k,
        score_threshold=score_threshold,
        strict=strict,
    )
    if isinstance(result, dict) and "response" in result:
        return str(result["response"])
    return str(result)


__all__ = [
    "translate_job_description",
    "search_recruiter_candidates",
    "chat_over_profile",
]
