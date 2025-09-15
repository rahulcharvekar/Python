from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone
import os

from app.core.config import settings
from app.utils.Logging.logger import logger


REG_PATH = Path(settings.UPLOAD_DIR) / "agent_files.json"


def _ensure_store() -> None:
    try:
        Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        if not REG_PATH.exists():
            REG_PATH.write_text(json.dumps({"version": 1, "files": []}, indent=2))
    except Exception as e:
        logger.warning("Failed to ensure agent file registry: %s", e)


def _load() -> Dict[str, Any]:
    _ensure_store()
    try:
        return json.loads(REG_PATH.read_text() or "{}") or {"version": 1, "files": []}
    except Exception as e:
        logger.warning("Failed to load agent file registry: %s", e)
        return {"version": 1, "files": []}


def _save(data: Dict[str, Any]) -> None:
    _ensure_store()
    try:
        tmp = REG_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        os.replace(tmp, REG_PATH)
    except Exception as e:
        logger.warning("Failed to save agent file registry: %s", e)


def register(agent: str, *, filename: str, filepath: str, filehash: str, size: int, content_type: str | None = None) -> None:
    """Upsert an entry for (agent, filename) with file metadata."""
    data = _load()
    files = data.setdefault("files", [])

    iso = datetime.now(timezone.utc).isoformat()
    ext = Path(filename).suffix.lower()
    # Find existing by agent+filename
    found = None
    for entry in files:
        if entry.get("agent") == agent and entry.get("file") == filename:
            found = entry
            break

    payload = {
        "agent": agent,
        "file": filename,
        "path": str(filepath),
        "hash": filehash,
        "size": int(size),
        "ext": ext,
        "content_type": content_type or "",
        "uploaded_at": iso,
    }

    if found is None:
        files.append(payload)
    else:
        found.update(payload)

    _save(data)
    logger.info("Agent-file mapping saved | agent=%s | file=%s", agent, filename)


def list_for_agent(agent: str) -> list[str]:
    """Return filenames registered for the given agent."""
    data = _load()
    out: list[str] = []
    for entry in data.get("files", []) or []:
        if entry.get("agent") == agent:
            fn = entry.get("file")
            if isinstance(fn, str):
                out.append(fn)
    return out


def is_allowed(agent: str, filename: str) -> bool:
    """Check whether (agent, filename) is present in the registry."""
    data = _load()
    for entry in data.get("files", []) or []:
        if entry.get("agent") == agent and entry.get("file") == filename:
            return True
    return False
