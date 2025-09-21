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
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(agent, file)
            )
            """
        )
        conn.commit()


def upsert_document(
    *,
    agent: str,
    file: str,
    vector_collection: str,
    title: Optional[str] = None,
) -> None:
    _ensure_schema()
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        payload = dict(
            agent=agent,
            file=file,
            title=title,
            vector_collection=vector_collection,
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
                    updated_at=:updated_at
                WHERE agent=:agent AND file=:file
                """,
                payload,
            )
        else:
            conn.execute(
                """
                INSERT INTO documents (
                    agent, file, title, vector_collection, created_at, updated_at
                ) VALUES (
                    :agent, :file, :title, :vector_collection, :created_at, :updated_at
                )
                """,
                payload,
            )
        conn.commit()


def list_documents(agent: str) -> List[Dict[str, Any]]:
    _ensure_schema()
    with _connect() as conn:
        cur = conn.execute(
            "SELECT agent, file, title, vector_collection, created_at, updated_at FROM documents WHERE agent=? ORDER BY updated_at DESC",
            (agent,),
        )
        rows = cur.fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "agent": r[0],
                "file": r[1],
                "title": r[2],
                "vector_collection": r[3],
                "created_at": r[4],
                "updated_at": r[5],
            }
        )
    return out
