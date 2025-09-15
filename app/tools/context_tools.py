from langchain_core.tools import tool
from typing import Optional
import re


def _normalize_query_basic_local(q: str) -> str:
    """Best-effort light normalization to improve retrieval on chatty/typoed prompts."""
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
    Normalize a chatty/typoed query to improve retrieval.
    Returns a normalized variant (lowercased, typos fixed, filler removed).
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
    Retrieve high-signal context blocks for a file and query, ready for LLM use.

    Returns a concise, human-readable summary with scores and previews.
    """
    try:
        from app.services import chat_service
        hits = chat_service.retrieve(
            file,
            query,
            k=k,
            score_threshold=score_threshold,
            strict=strict,
        )
        if not hits and retry_normalized:
            norm = _normalize_query_basic_local(query)
            if norm and norm.strip() and norm.strip() != query.strip().lower():
                hits = chat_service.retrieve(
                    file,
                    norm,
                    k=k,
                    score_threshold=score_threshold,
                    strict=strict,
                )

        if not hits:
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
        return "\n\n".join(lines)
    except Exception as e:
        return f"Error building context: {e}"
