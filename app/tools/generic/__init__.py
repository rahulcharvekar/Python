from __future__ import annotations

from langchain_core.tools import tool
from typing import List, Dict
import re

from app.services.generic import profile_text
from app.services.generic import chat_service
from app.services.generic import insight_services
from app.services.generic import ingestion_db


def _extract_keywords(text: str, max_k: int = 40) -> List[str]:
    s = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    tokens = [t for t in s.split() if t]
    stop = {
        "and","or","the","a","an","is","are","with","in","of","to","for","on","at","by","as","be",
        "this","that","it","from","was","were","am","i","we","you","they","he","she","have","has","had",
        "my","our","their","your","over","using","use","used","etc","pdf","doc","docx","txt","resume","cv",
        "csv","xlsx","md","file","document",
    }
    counts: Dict[str, int] = {}
    for t in tokens:
        if t in stop or len(t) < 2:
            continue
        counts[t] = counts.get(t, 0) + 1
    return [term for term, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:max_k]]


@tool("extract_keywords")
def extract_keywords(file: str) -> str:
    """
    Extract up to ~40 frequent keywords from an uploaded file's text.
    Returns: { file, loader, keywords }
    """
    try:
        text, loader = profile_text.load_text(file)
        kws = _extract_keywords(text)
        return str({"file": file, "loader": loader, "keywords": kws})
    except Exception as e:
        return str({"file": file, "error": str(e)})


# chat_over_file is agent-facing (DocHelp); implemented in app/tools/agent/dochelp_tools.py


# --- Vector index management ---
@tool("initialize_insights")
def initialize_insights(file: str, force: bool = False) -> str:
    """
    Initialize or update the vector index for the specified uploaded file.

    Args:
        file: Filename under the uploads directory (e.g., mydoc.pdf).
        force: When true, rebuilds the index from scratch.

    Returns:
        A status message string.
    """
    try:
        vs = insight_services.create_vector_store(file, force=force)
        if vs:
            return f"AI is initialized for file: {file} (force={force})"
        return f"No vector store created for file: {file}"
    except Exception as e:
        return f"Error initializing AI Assistant for file: {file}: {e}"


@tool("check_file_ready")
def check_file_ready(file: str) -> str:
    """
    Check whether the specified file has been vectorized and is ready for chat_over_file.

    Args:
        file: Filename under the uploads directory (e.g., mydoc.pdf).

    Returns:
        A JSON-like string with: file, file_exists, collection, vector_count, ready.
    """
    try:
        status = insight_services.check_vector_ready(file)
        return str(status)
    except Exception as e:
        return str({"file": file, "ready": False, "error": str(e)})


@tool("reindex_file")
def reindex_file(file: str) -> str:
    """
    Force-rebuild the vector index for a file (drops and recreates the collection).

    Args:
        file: Filename under the uploads directory.

    Returns:
        A short status message.
    """
    try:
        insight_services.create_vector_store(file, force=True)
        return f"Re-indexed: {file}"
    except Exception as e:
        return f"Failed to re-index {file}: {e}"


# --- Query normalization and context building ---
def _normalize_query_basic_local(q: str) -> str:
    s = q.lower()
    replacements = {
        r"\bu\b": "you",
        r"\bur\b": "your",
        r"\bplz\b|\bpls\b": "please",
        r"\bgve\b": "give",
        r"\bcud\b": "could",
        r"\bcn\b": "can",
    }
    for pat, rep in replacements.items():
        s = re.sub(pat, rep, s)
    s = re.sub(r"\b([a-z]+)'s\b", r"\1", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    tokens = [t for t in s.split() if t]
    stop = {
        "can","could","please","kindly","tell","give","provide","me","about","details",
        "would","should","the","a","an","is","are","be","on","in","for","of","to",
    }
    kept = [t for t in tokens if t not in stop]
    return " ".join(kept)


@tool("normalize_query")
def normalize_query(query: str) -> str:
    """
    Normalize a chatty/typoed query to improve retrieval by lowercasing,
    fixing common shorthand, and removing filler tokens.

    Args:
        query: User-provided natural language query.

    Returns:
        A normalized query string.
    """
    try:
        return _normalize_query_basic_local(query)
    except Exception as e:
        return f"Error normalizing query: {e}"


@tool("build_context")
def build_context(
    file: str,
    query: str,
    k: int = 8,
    score_threshold: float = 0.45,
    strict: bool = True,
    retry_normalized: bool = True,
    max_blocks: int = 5,
    preview_chars: int = 240,
) -> str:
    """
    Retrieve high-signal context blocks for a file and query, summarized for LLM use.

    Returns a concise, human-readable summary with scores and previews.
    """
    try:
        hits = chat_service.retrieve(
            file,
            query,
            k=k,
            score_threshold=score_threshold,
        )
        if not hits and retry_normalized:
            norm = _normalize_query_basic_local(query)
            if norm and norm.strip() and norm.strip() != query.strip().lower():
                hits = chat_service.retrieve(
                    file,
                    norm,
                    k=k,
                    score_threshold=score_threshold,
                )

        if not hits and strict:
            return "No strong matches found (context empty)."

        def _preview(txt: str) -> str:
            t = (txt or "").strip().replace("\n", " ")
            return (t[:preview_chars] + ("..." if len(t) > preview_chars else ""))

        lines = []
        for i, (doc, meta, score) in enumerate(hits[:max_blocks], start=1):
            src = meta.get("source") if isinstance(meta, dict) else None
            pg = meta.get("page") if isinstance(meta, dict) else None
            parts = [f"[{i}] score={round(score,3)}"]
            if src:
                parts.append(f"source={src}")
            if pg is not None:
                parts.append(f"page={pg}")
            header = " | ".join(parts)
            lines.append(f"{header}\n{_preview(doc)}")
        return "\n\n".join(lines) if lines else "No strong matches found (context empty)."
    except Exception as e:
        return f"Error building context: {e}"


# --- Agent file registry utility ---
@tool("list_agent_files")
def list_agent_files(agent: str) -> str:
    """
    List files registered for the specified agent (from the JSON registry under uploads).

    Args:
        agent: Agent name to filter by (e.g., DocHelp, Recruiter).

    Returns:
        A JSON-like string: { files: [...] }.
    """
    try:
        rows = ingestion_db.list_documents(agent)
        files: List[str] = []
        for r in rows:
            fn = r.get("file") if isinstance(r, dict) else None
            if isinstance(fn, str):
                files.append(fn)
        # De-duplicate in case same file has multiple doc_types
        uniq = sorted(list(dict.fromkeys(files)))
        return str({"files": uniq})
    except Exception as e:
        return str({"files": [], "error": str(e)})
