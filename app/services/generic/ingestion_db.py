from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from app.core.config import settings


# Use a shared DB directory for all agents
DB_PATH = Path(settings.DB_DIR) / "ingestion.sqlite3"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _ensure_schema() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                file TEXT NOT NULL,
                title TEXT,                       -- display name or inferred subject
                vector_collection TEXT,           -- collection name in vector DB
                keywords TEXT,                    -- JSON array of keywords/skills
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(agent, file)
            )
            """
        )
        try:
            conn.execute("ALTER TABLE documents ADD COLUMN keywords TEXT")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        conn.commit()


def _ensure_search_schema() -> None:
    # FTS disabled: no-op to keep backward import compatibility
    return None


def _serialize_keywords(keywords: Optional[Any]) -> Optional[str]:
    if keywords is None:
        return None
    if isinstance(keywords, str):
        try:
            # Ensure valid JSON list
            parsed = json.loads(keywords)
            if isinstance(parsed, list):
                cleaned = [str(k).lower().strip() for k in parsed if isinstance(k, (str, int))]
                return json.dumps([k for k in cleaned if k])
        except json.JSONDecodeError:
            pass
        cleaned = [str(keywords).lower().strip()]
        return json.dumps([k for k in cleaned if k])
    if isinstance(keywords, (list, tuple, set)):
        cleaned = [str(k).lower().strip() for k in keywords if isinstance(k, (str, int))]
        deduped = list(dict.fromkeys([k for k in cleaned if k]))
        return json.dumps(deduped)
    return None


def upsert_document(
    *,
    agent: str,
    file: str,
    vector_collection: str,
    title: Optional[str] = None,
    keywords: Optional[Any] = None,
) -> None:
    _ensure_schema()
    now = datetime.now(timezone.utc).isoformat()
    serialized_keywords = _serialize_keywords(keywords)
    with _connect() as conn:
        payload = dict(
            agent=agent,
            file=file,
            title=title,
            vector_collection=vector_collection,
            keywords=serialized_keywords,
            created_at=now,
            updated_at=now,
        )
        cur = conn.execute(
            "SELECT id FROM documents WHERE agent=? AND file=?",
            (agent, file),
        )
        row = cur.fetchone()
        if row:
            payload["updated_at"] = now
            conn.execute(
                """
                UPDATE documents SET
                    title=:title,
                    vector_collection=:vector_collection,
                    keywords=:keywords,
                    updated_at=:updated_at
                WHERE agent=:agent AND file=:file
                """,
                payload,
            )
        else:
            conn.execute(
                """
                INSERT INTO documents (
                    agent, file, title, vector_collection, keywords, created_at, updated_at
                ) VALUES (
                    :agent, :file, :title, :vector_collection, :keywords, :created_at, :updated_at
                )
                """,
                payload,
            )
        conn.commit()


def list_documents(agent: str) -> List[Dict[str, Any]]:
    _ensure_schema()
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT agent, file, title, vector_collection, keywords, created_at, updated_at
            FROM documents
            WHERE agent=?
            ORDER BY updated_at DESC
            """,
            (agent,),
        )
        rows = cur.fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        keywords: List[str] = []
        raw_keywords = r[4]
        if isinstance(raw_keywords, str) and raw_keywords:
            try:
                parsed = json.loads(raw_keywords)
                if isinstance(parsed, list):
                    keywords = [str(k).lower() for k in parsed if isinstance(k, (str, int))]
            except json.JSONDecodeError:
                keywords = [raw_keywords.lower()]
        out.append(
            {
                "agent": r[0],
                "file": r[1],
                "title": r[2],
                "vector_collection": r[3],
                "keywords": keywords,
                "created_at": r[5],
                "updated_at": r[6],
            }
        )
    return out


def upsert_doc_keywords(
    *,
    agent: str,
    file: str,
    title: Optional[str],
    keywords: List[str] | None,
    skills: List[str] | None,
) -> None:
    # FTS disabled: no-op to maintain compatibility
    return None


def search_doc_keywords(agent: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """FTS disabled: return empty results."""
    return []
