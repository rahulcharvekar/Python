from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from app.services.generic import ingestion_db, insight_services


def ingest_document(file: str, *, agent: str = "dochelp") -> Dict[str, Any]:
    # Obtain vector collection from DB (set during upload indexing). Do not create here.
    try:
        rows = ingestion_db.list_documents(agent)
        row = next((r for r in rows if isinstance(r, dict) and r.get("file") == file), None)
        collection = (row or {}).get("vector_collection") if isinstance(row, dict) else None
    except Exception:
        collection = None

    stem = Path(file).stem
    ingestion_db.upsert_document(
        agent=agent,
        file=file,
        title=stem,
        vector_collection=str(collection or ""),
        keywords=None,
    )

    # Add a compact facts document into the same vector collection to help retrieval
    try:
        facts_lines = [
            f"Title: {stem}",
            f"SourceFile: {file}",
        ]
        insight_services.add_facts_document(
            file,
            "\n".join(facts_lines),
            metadata={"type": "facts", "title": stem},
        )
    except Exception:
        pass
    return {
        "file": file,
        "collection": collection,
        "title": stem,
        "keywords": [],
    }


def list_indexed_docs(agent: str = "dochelp") -> List[Dict[str, Any]]:
    rows = ingestion_db.list_documents(agent)
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "file": r.get("file"),
                "title": r.get("title"),
                "vector_collection": r.get("vector_collection"),
                "keywords": r.get("keywords"),
                "updated_at": r.get("updated_at"),
            }
        )
    return out
