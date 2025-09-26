from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.agent_factory import _create_llm
from app.services.generic import ingestion_db, chat_service
from app.utils.Logging.logger import logger


AGENT_NAME = "recruiter"


@dataclass
class CandidateMatch:
    file: str
    candidate_name: str
    score: float
    highlight: str
    vector_collection: str | None
    keywords: List[str] | None
    metadata: Dict[str, Any] | None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "candidate_name": self.candidate_name,
            "matching_score": round(self.score * 100, 1),
            "raw_score": round(self.score, 4),
            "highlight": self.highlight,
            "vector_collection": self.vector_collection,
            "keywords": self.keywords or [],
            "source_metadata": self.metadata or {},
        }


def _is_probably_english(text: str) -> bool:
    if not text:
        return True
    ascii_chars = sum(1 for ch in text if ch.isascii())
    ratio = ascii_chars / max(len(text), 1)
    return ratio >= 0.85


def translate_description(description: str) -> Tuple[str, bool]:
    """Translate job description to English when needed.

    Returns the translated text and a flag indicating whether translation occurred.
    """
    cleaned = (description or "").strip()
    if not cleaned:
        return "", False

    if _is_probably_english(cleaned):
        return cleaned, False

    try:
        llm = _create_llm(None)
        prompt = (
            "Translate the following job description into clear English. "
            "If the text is already in English, return it unchanged. "
            "Respond with only the translated text.\n\n"
            f"Job description:\n{cleaned}"
        )
        result = llm.invoke(
            [
                SystemMessage(content="You translate job descriptions to English while preserving intent."),
                HumanMessage(content=prompt),
            ]
        )
        translated = (getattr(result, "content", "") or "").strip()
        if translated:
            changed = translated.lower() != cleaned.lower()
            return translated, changed
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Recruiter translation failed; using original text | error=%s", exc)
    return cleaned, False


def _list_candidate_records() -> List[Dict[str, Any]]:
    try:
        return ingestion_db.list_documents(AGENT_NAME)
    except Exception as exc:
        logger.error("Unable to list recruiter documents | error=%s", exc)
        return []


def search_candidates(query: str, *, max_results: int = 5) -> List[CandidateMatch]:
    records = _list_candidate_records()
    matches: List[CandidateMatch] = []

    for record in records:
        file = record.get("file") if isinstance(record, dict) else None
        if not isinstance(file, str):
            continue

        try:
            hits = chat_service.retrieve(
                file,
                query,
                k=5,
                score_threshold=0.45,
                strict=False,
            )
        except Exception as exc:
            logger.warning(
                "Recruiter search skipped file due to retrieval failure | file=%s | error=%s",
                file,
                exc,
            )
            continue

        if not hits:
            logger.debug(
                "Recruiter search found no hits above threshold | file=%s | query=%s",
                file,
                query,
            )
            continue

        top_doc, top_meta, top_score = hits[0]
        snippet = (top_doc or "").strip().replace("\n", " ")
        if len(snippet) > 320:
            snippet = snippet[:317].rstrip() + "..."

        candidate_name = record.get("title") or Path(file).stem
        keywords = record.get("keywords") if isinstance(record, dict) else None
        vector_collection = record.get("vector_collection") if isinstance(record, dict) else None
        metadata = top_meta if isinstance(top_meta, dict) else None

        matches.append(
            CandidateMatch(
                file=file,
                candidate_name=candidate_name,
                score=float(top_score),
                highlight=snippet,
                vector_collection=vector_collection,
                keywords=keywords if isinstance(keywords, list) else None,
                metadata=metadata,
            )
        )

    matches.sort(key=lambda m: m.score, reverse=True)
    logger.info(
        "Recruiter search candidates completed | query=%.40s | results=%d",
        query,
        len(matches),
    )
    return matches[:max_results]


__all__ = [
    "translate_description",
    "search_candidates",
    "CandidateMatch",
]
