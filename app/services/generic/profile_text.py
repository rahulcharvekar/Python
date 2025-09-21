from __future__ import annotations

from pathlib import Path
from typing import Tuple


def load_text(file: str) -> Tuple[str, str]:
    """Return (text, loader_name) by inferring from extension. Supports pdf/docx/txt/md; .doc best-effort via unstructured if installed."""
    from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
    try:
        from langchain_community.document_loaders import UnstructuredFileLoader  # optional
        has_unstructured = True
    except Exception:
        UnstructuredFileLoader = None  # type: ignore
        has_unstructured = False

    p = Path(file)
    if not p.is_absolute():
        from app.core.config import settings
        base = Path(settings.BASE_DIR) / file
        p = base if base.exists() else Path(settings.UPLOAD_DIR) / file

    ext = p.suffix.lower()
    if ext == ".pdf":
        docs = PyPDFLoader(str(p)).load()
        return "\n\n".join(d.page_content or "" for d in docs), "PyPDFLoader"
    if ext == ".docx":
        docs = Docx2txtLoader(str(p)).load()
        return "\n\n".join(d.page_content or "" for d in docs), "Docx2txtLoader"
    if ext == ".doc" and has_unstructured:
        docs = UnstructuredFileLoader(str(p)).load()
        return "\n\n".join(d.page_content or "" for d in docs), "UnstructuredFileLoader"
    if ext in {".txt", ".md"}:
        docs = TextLoader(str(p), encoding="utf-8").load()
        return "\n\n".join(d.page_content or "" for d in docs), "TextLoader"
    raise ValueError(f"Unsupported file type: {ext}")

