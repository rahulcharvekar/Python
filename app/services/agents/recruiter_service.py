from __future__ import annotations

from typing import List, Dict, Any, Tuple

from app.services.generic import profile_text, ingestion_db, chat_service
from app.services.generic import intent_service


def enrich_resume(file: str, *, agent: str = "Recruiter") -> Dict[str, Any]:
    # Minimal enrichment without regex: persist document row; skip keyword/skill extraction.
    _text, loader = profile_text.load_text(file)
    try:
        rows = ingestion_db.list_documents(agent)
        row = next((r for r in rows if isinstance(r, dict) and r.get("file") == file), None)
        collection = (row or {}).get("vector_collection") if isinstance(row, dict) else None
    except Exception:
        collection = None

    ingestion_db.upsert_document(agent=agent, file=file, title=None, vector_collection=str(collection or ""))

    return {
        "file": file,
        "loader": loader,
        "collection": collection,
        "skills": [],
        "name": None,
    }


def list_indexed_profiles(agent: str = "Recruiter") -> List[Dict[str, Any]]:
    try:
        rows = ingestion_db.list_documents(agent)
    except Exception:
        rows = []
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "file": r.get("file"),
                "name": r.get("title"),
                "vector_collection": r.get("vector_collection"),
                "updated_at": r.get("updated_at"),
            }
        )
    return out


# Removed legacy search_profiles (keyword-less vector sweep). Use search_profiles_intent_llm.


def search_profiles_keyword(query: str, *, agent: str = "Recruiter", limit: int = 20) -> List[Dict[str, Any]]:
    """Deprecated: keyword search removed (FTS disabled)."""
    return []


def _language_tokens() -> set:
    return {
        "java", "j2ee", "spring", "springboot", "microservices",
        "python", "django", "flask", "fastapi",
        "javascript", "typescript", "node", "nodejs", "react",
        "c", "c++", "cpp", "c#", "csharp",
        "go", "golang", "ruby", "rails", "php",
        "scala", "kotlin", "rust", "swift", "objective-c",
    }


def search_profiles_intent_llm(
    query: str,
    *,
    agent: str = "Recruiter",
    shortlist_limit: int = 50,
    k_per_file: int = 8,
) -> List[Dict[str, Any]]:
    """
    One-shot LLM intent parsing + vector ranking.

    - Parse criteria once via LLM (cheap) into structured filters
    - Optionally shortlist via FTS over enriched keywords/skills
    - Retrieve over shortlisted files and compute a composite score
    """
    # 1) Parse criteria
    criteria = intent_service.parse_criteria_llm(query)
    rewritten = intent_service.rewrite_query(criteria)

    # 2) Build metadata map and optional shortlist via FTS
    try:
        rows_kw = ingestion_db.list_documents(agent)
    except Exception:
        rows_kw = []
    by_file = {r.get("file"): r for r in rows_kw if isinstance(r, dict)}

    # Candidates: all files (FTS disabled); rely on vectors for ranking.
    candidates: List[str] = [f for f in by_file.keys()]

    # 3) Retrieve and score
    min_score = 0.30
    lang_tokens = _language_tokens()
    include = set(criteria.get("include_skills") or [])
    required = set(criteria.get("required_skills") or [])
    optional = set(criteria.get("optional_skills") or [])
    exclude = set(criteria.get("exclude_skills") or [])
    require_all = bool(criteria.get("require_all"))
    must_only = bool(criteria.get("must_only"))
    min_years = criteria.get("min_years")
    locs = set((criteria.get("locations") or []))
    titles = set((criteria.get("titles") or []))
    seniority = set((criteria.get("seniority_levels") or []))
    domains = set((criteria.get("domains") or []))
    top_n = criteria.get("top_n") if isinstance(criteria.get("top_n"), int) else None

    ranked: List[Tuple[str, float]] = []
    for f in candidates:
        try:
            hits = chat_service.retrieve(f, rewritten, k=k_per_file, score_threshold=min_score, strict=True)
            if not hits:
                continue
            best = max((s for (_d, _m, s) in hits), default=0.0)
            if best < min_score:
                continue

            # Heuristic boosts/penalties from metadata and retrieved text
            # Present tokens helper
            meta = by_file.get(f, {})
            text_blob = "\n".join(d for (d, _m, _s) in hits[:3] if isinstance(d, str)).lower()
            def _has(token: str) -> bool:
                t = (token or "").lower().strip()
                return bool(t) and (t in text_blob)

            # Hard gates
            req_set = set(required)
            if require_all and not req_set:
                req_set = set(include)
            if req_set and any(not _has(s) for s in req_set):
                continue  # missing a mandatory skill
            if exclude and any(_has(s) for s in exclude):
                continue  # explicitly excluded present

            boost = 0.0
            # location boost (from retrieved text only)
            if any((loc or "") in text_blob for loc in locs if loc):
                boost += 0.05

            # years evidence: regex removed; skip boosting to keep runtime lightweight

            # "only" penalty if many other languages appear besides include
            if must_only and include:
                present_langs = {t for t in lang_tokens if t in text_blob}
                extras_langs = present_langs - include
                if len(extras_langs) >= 2:
                    boost -= 0.08
                elif len(extras_langs) == 1:
                    boost -= 0.04

            # Optional skills small boosts
            if optional:
                opt_matches = sum(1 for s in optional if _has(s))
                boost += min(0.06, 0.02 * opt_matches)

            # Titles / seniority / domains small boosts
            if titles and any(_has(t) for t in titles):
                boost += 0.03
            if seniority and any(_has(s) for s in seniority):
                boost += 0.02
            if domains and any(_has(d) for d in domains):
                boost += 0.03

            final = max(0.0, min(1.0, float(best) + boost))
            ranked.append((f, final))
        except Exception:
            continue

    ranked.sort(key=lambda x: x[1], reverse=True)
    out: List[Dict[str, Any]] = []
    for f, score in (ranked[:top_n] if top_n and top_n > 0 else ranked):
        meta = by_file.get(f, {})
        out.append({
            "file": f,
            "best_score": round(score, 3),
            "name": meta.get("title"),
            "vector_collection": meta.get("vector_collection"),
        })
    return out
