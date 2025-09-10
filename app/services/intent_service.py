import re
from typing import List, Optional, Tuple, Dict, Any


FILE_EXT_PATTERN = re.compile(r"\b([\w\-\s]+\.(pdf|csv|docx|xlsx|txt))\b", re.IGNORECASE)


def _normalize_name(name: str) -> str:
    return name.strip().lower()


def detect_file_intent(query: str, known_files: List[str]) -> Dict[str, Any]:
    """
    Lightweight, local intent detector to avoid LLM calls when the user's
    query isn't about uploaded files or RAG actions.

    Returns:
      {
        "is_file_intent": bool,
        "matched_file": Optional[str],  # exact UI filename if matched
        "reason": str,                  # brief reason for decision
      }
    """
    q = (query or "").strip()
    if not q:
        return {"is_file_intent": False, "matched_file": None, "reason": "empty"}

    # Explicit filename mention
    match = FILE_EXT_PATTERN.search(q)
    if match:
        mentioned = match.group(1).strip()
        # Try to match against known filenames (case-insensitive)
        norm_known = {_normalize_name(f): f for f in known_files}
        resolved = norm_known.get(_normalize_name(mentioned))
        return {
            "is_file_intent": True,
            "matched_file": resolved or mentioned,
            "reason": "explicit_filename",
        }

    # Keyword-based detection: references to docs/files or RAG ops
    keywords = [
        "file", "document", "pdf", "csv", "section", "page",
        "summarize", "from the file", "in the document",
        "initialize", "index", "ingest", "vectorize", "get insights",
        "chroma", "embedding",
        "upload", "attach",
    ]
    lowered = q.lower()
    if any(kw in lowered for kw in keywords):
        return {"is_file_intent": True, "matched_file": None, "reason": "keywords"}

    return {"is_file_intent": False, "matched_file": None, "reason": "no_file_signals"}

