from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Tuple
import re

from app.services.generic import profile_text, ingestion_db, insight_services, chat_service
from app.core.config import settings
from app.utils.fileops.fileutils import hash_file
import os


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


def _extract_emails(text: str) -> List[str]:
    return sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")))


def _extract_phones(text: str) -> List[str]:
    return sorted(set(re.findall(r"\+?\d[\d\-\s()]{8,}\d", text or "")))


def _extract_total_experience(text: str) -> int | None:
    vals = [int(m) for m in re.findall(r"(\d{1,2})\s*(?:\+\s*)?(?:years|yrs)\b", text or "", flags=re.IGNORECASE)]
    return max(vals) if vals else None


def _extract_skills(text: str) -> List[str]:
    skill_keywords = [
        "java","spring","springboot","microservices","kafka","aws","gcp","azure","python","sql",
        "spark","hadoop","airflow","docker","kubernetes","rest","graphql","react","node","django",
    ]
    norm = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    tokens = set(norm.split())
    return sorted({k for k in skill_keywords if k in tokens})


def _extract_person_name_from_email(emails: List[str]) -> str | None:
    for em in emails or []:
        try:
            local = em.split("@", 1)[0]
            local = re.sub(r"[._-]+", " ", local)
            words = [w for w in local.split() if w and w.isalpha()]
            if 1 < len(words) <= 4:
                return " ".join(w.capitalize() for w in words)
        except Exception:
            continue
    return None


def enrich_resume(file: str, *, agent: str = "Recruiter") -> Dict[str, Any]:
    text, loader = profile_text.load_text(file)
    emails = _extract_emails(text)
    phones = _extract_phones(text)
    total_exp = _extract_total_experience(text)
    skills = _extract_skills(text)
    person_name = _extract_person_name_from_email(emails)
    keywords = _extract_keywords(text)

    # Obtain vector collection name from DB (upload flow writes it). Do not create here.
    try:
        rows = ingestion_db.list_documents(agent)
        row = next((r for r in rows if isinstance(r, dict) and r.get("file") == file), None)
        collection = (row or {}).get("vector_collection") if isinstance(row, dict) else None
    except Exception:
        collection = None

    # Persist generic document row
    ingestion_db.upsert_document(agent=agent, file=file, title=person_name, vector_collection=str(collection or ""))

    # Also add a compact facts document into the vector collection to boost retrieval
    try:
        facts_lines = [
            f"Name: {person_name or ''}",
            f"Emails: {', '.join(emails or [])}",
            f"Phones: {', '.join(phones or [])}",
            f"TotalExperienceYears: {total_exp if total_exp is not None else ''}",
            f"Skills: {', '.join(skills or [])}",
            f"Keywords: {', '.join(keywords or [])}",
            f"SourceFile: {file}",
        ]
        facts_text = "\n".join(facts_lines)
        insight_services.add_facts_document(
            file,
            facts_text,
            metadata={
                "type": "facts",
                "name": person_name or "",
                "skills": skills or [],
                "total_experience_years": total_exp if total_exp is not None else None,
                "emails": emails or [],
                "phones": phones or [],
            },
        )
    except Exception:
        pass

    return {
        "file": file,
        "loader": loader,
        "collection": collection,
        "skills": skills,
        "name": person_name,
    }


def list_indexed_profiles(agent: str = "Recruiter") -> List[Dict[str, Any]]:
    rows = ingestion_db.list_documents(agent)
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "file": r.get("file"),
                "name": r.get("title"),
                "vector_collection": r.get("vector_collection"),
                "keywords_count": len(r.get("keywords") or []),
                "skills": r.get("tags"),
                "updated_at": r.get("updated_at"),
            }
        )
    return out


def search_profiles(query: str, *, agent: str = "Recruiter", k_per_file: int = 4) -> List[Dict[str, Any]]:
    """
    Search across all indexed resumes for the given agent and return a ranked list.

    Strategy: for each file registered to the agent, run vector retrieval with a
    lenient threshold to get top matches, track the best normalized score, and sort
    files by that score desc.

    Returns a list of { file, best_score, name, vector_collection }.
    """
    try:
        rows = ingestion_db.list_documents(agent)
        files = [r.get("file") for r in rows if isinstance(r, dict) and isinstance(r.get("file"), str)]
    except Exception:
        files = []

    ranked: List[Tuple[str, float]] = []
    best_meta: Dict[str, Dict[str, Any]] = {}
    for f in files:
        try:
            hits = chat_service.retrieve(f, query, k=k_per_file, score_threshold=0.35, strict=False)
            best = max((s for (_d, _m, s) in hits), default=0.0)
            ranked.append((f, float(best)))
            # store name/vector_collection for convenience
            row = next((r for r in rows if r.get("file") == f), {})
            best_meta[f] = {
                "name": row.get("title"),
                "vector_collection": row.get("vector_collection"),
            }
        except Exception:
            continue

    ranked.sort(key=lambda x: x[1], reverse=True)
    out: List[Dict[str, Any]] = []
    for f, score in ranked:
        meta = best_meta.get(f, {})
        out.append({
            "file": f,
            "best_score": round(score, 3),
            "name": meta.get("name"),
            "vector_collection": meta.get("vector_collection"),
        })
    return out
