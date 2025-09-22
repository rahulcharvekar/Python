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


def _ensure_search_schema() -> None:
    """Ensure the FTS5 table for keyword/skills search exists."""
    with _connect() as conn:
        # Use a simple content table with FTS5 across title, keywords, skills
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS doc_search USING fts5(
                agent UNINDEXED,
                file UNINDEXED,
                title,
                keywords,
                skills,
                tokenize='porter'
            );
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


def list_documents_with_keywords(agent: str) -> List[Dict[str, Any]]:
    """List documents with FTS keywords/skills joined if present."""
    _ensure_schema()
    _ensure_search_schema()
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT d.agent, d.file, d.title, d.vector_collection, d.created_at, d.updated_at,
                   COALESCE(s.keywords, ''), COALESCE(s.skills, '')
            FROM documents d
            LEFT JOIN doc_search s ON d.agent = s.agent AND d.file = s.file
            WHERE d.agent = ?
            ORDER BY d.updated_at DESC
            """,
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
                "keywords": r[6] or "",
                "skills": r[7] or "",
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
    """Insert or replace keyword/skill rows for a document into the FTS table."""
    _ensure_search_schema()
    kw_text = " ".join((keywords or []))
    sk_text = " ".join((skills or []))
    with _connect() as conn:
        # Remove any prior row for this doc to avoid duplicates
        conn.execute("DELETE FROM doc_search WHERE agent=? AND file=?", (agent, file))
        conn.execute(
            "INSERT INTO doc_search(agent, file, title, keywords, skills) VALUES (?, ?, ?, ?, ?)",
            (agent, file, title or "", kw_text, sk_text),
        )
        conn.commit()


def search_doc_keywords(agent: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Run a keyword search over title/keywords/skills using SQLite FTS5.

    Returns rows with file, title, score (bm25 where lower=better), and a rank.
    """
    _ensure_search_schema()
    with _connect() as conn:
        try:
            cur = conn.execute(
                """
                SELECT file, title, bm25(doc_search) AS score
                FROM doc_search
                WHERE agent = ? AND doc_search MATCH ?
                ORDER BY score ASC
                LIMIT ?
                """,
                (agent, query, int(limit)),
            )
        except Exception:
            # Fallback if bm25 is unavailable: no score, order undefined
            cur = conn.execute(
                """
                SELECT file, title, 0.0 as score
                FROM doc_search
                WHERE agent = ? AND doc_search MATCH ?
                LIMIT ?
                """,
                (agent, query, int(limit)),
            )
        rows = cur.fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({
            "file": r[0],
            "title": r[1],
            "score": float(r[2]) if isinstance(r[2], (int, float)) else 0.0,
        })
    return out
