from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any
import re

from app.services.generic import profile_text, ingestion_db, insight_services


def _extract_keywords(text: str, max_k: int = 40) -> List[str]:
    s = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    tokens = [t for t in s.split() if t]
    stop = {
        "and","or","the","a","an","is","are","with","in","of","to","for","on","at","by","as","be",
        "this","that","it","from","was","were","am","i","we","you","they","he","she","have","has","had",
        "over","using","use","used","etc","pdf","doc","docx","txt","csv","xlsx","md","file","document",
    }
    counts: Dict[str, int] = {}
    for t in tokens:
        if t in stop or len(t) < 2:
            continue
        counts[t] = counts.get(t, 0) + 1
    return [term for term, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:max_k]]


def ingest_document(file: str, *, agent: str = "DocHelp") -> Dict[str, Any]:
    text, loader = profile_text.load_text(file)
    keywords = _extract_keywords(text)

    # Obtain vector collection from DB (set during upload indexing). Do not create here.
    try:
        rows = ingestion_db.list_documents(agent)
        row = next((r for r in rows if isinstance(r, dict) and r.get("file") == file), None)
        collection = (row or {}).get("vector_collection") if isinstance(row, dict) else None
    except Exception:
        collection = None

    stem = Path(file).stem
    ingestion_db.upsert_document(agent=agent, file=file, title=stem, vector_collection=str(collection or ""))

    # Add a compact facts document into the same vector collection to help retrieval
    try:
        facts_lines = [
            f"Title: {stem}",
            f"Keywords: {', '.join(keywords or [])}",
            f"SourceFile: {file}",
        ]
        insight_services.add_facts_document(
            file,
            "\n".join(facts_lines),
            metadata={"type": "facts", "title": stem, "keywords": keywords or []},
        )
    except Exception:
        pass
    return {
        "file": file,
        "loader": loader,
        "collection": collection,
        "title": stem,
    }


def list_indexed_docs(agent: str = "DocHelp") -> List[Dict[str, Any]]:
    rows = ingestion_db.list_documents(agent)
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "file": r.get("file"),
                "title": r.get("title"),
                "vector_collection": r.get("vector_collection"),
                "updated_at": r.get("updated_at"),
            }
        )
    return out
