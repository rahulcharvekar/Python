from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.utils.Logging.logger import logger
from app.services.generic import chat_service


_SYNONYMS = {
    "java": ["java", "j2ee", "spring", "springboot"],
    "python": ["python", "django", "flask", "fastapi"],
    "javascript": ["javascript", "js", "node", "nodejs", "react"],
    "csharp": ["c#", "csharp", ".net", "dotnet"],
    "golang": ["go", "golang"],
}

_LANGUAGE_TOKENS = {
    "java", "python", "javascript", "js", "typescript", "node", "nodejs",
    "react", "angular", "vue", "c", "c++", "cpp", "c#", "csharp", ".net", "dotnet",
    "go", "golang", "ruby", "rails", "php", "swift", "kotlin", "scala", "rust",
    "dart", "flutter", "spark", "hadoop", "sql", "nosql", "aws", "gcp", "azure",
}


def _heuristic_skills_from_query(query: str) -> List[str]:
    """Extract obvious skill tokens from raw text when LLM output is empty."""
    tokens = re.findall(r"[a-zA-Z0-9\+#\.]+", query.lower())
    hits: List[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in _LANGUAGE_TOKENS and token not in seen:
            seen.add(token)
            hits.append(token)
    return hits


def _llm_keywords_from_query(query: str) -> List[str]:
    """Ask the LLM for a compact keyword list when structured parsing is empty."""
    prompt = (
        "Extract up to 10 concise search keywords from the request below. "
        "Return STRICT JSON: {\\n  keywords: string[]\\n}. "
        "Use lowercase words or short phrases, omit duplicates, and include only items directly implied."
    )
    user = (query or "").strip()
    if not user:
        return []
    try:
        client = chat_service.client
        model = chat_service.CHAT_MODEL
        if hasattr(client, "chat_completions"):
            chat = client.chat_completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
        else:
            chat = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user},
                ],
                temperature=0,
            )
        raw = chat.choices[0].message.content or "{}"
        data = json.loads(raw)
        keywords = data.get("keywords") or []
        cleaned = [str(k).lower().strip() for k in keywords if isinstance(k, (str, int))]
        deduped = list(dict.fromkeys([k for k in cleaned if k]))
        return deduped
    except Exception as exc:
        try:
            logger.debug("intent_service keyword fallback failed: %s", exc)
        except Exception:
            pass
        return []


def _llm_parse(query: str) -> Optional[Dict[str, Any]]:
    """Parse criteria via one-shot LLM. Returns dict or None on failure."""
    try:
        system = (
            "Extract structured hiring criteria from the user text. Return STRICT JSON only. "
            "Schema: {\n"
            "  include_skills: string[],            -- general skills mentioned\n"
            "  required_skills: string[],           -- explicitly mandatory/must-have\n"
            "  optional_skills: string[],           -- nice to have/plus\n"
            "  exclude_skills: string[],            -- explicitly not wanted\n"
            "  require_all: boolean,                -- if all listed skills must be present\n"
            "  must_only: boolean,                  -- e.g., 'java only'\n"
            "  min_years: integer|null,             -- minimum total experience\n"
            "  max_years: integer|null,\n"
            "  recent_years: integer|null,          -- e.g., 'last 3 years in X'\n"
            "  locations: string[],                 -- city/region tokens\n"
            "  titles: string[],                    -- roles/titles\n"
            "  seniority_levels: string[],          -- e.g., senior, lead\n"
            "  domains: string[],                   -- e.g., payments, fintech\n"
            "  remote_mode: 'any'|'remote'|'hybrid'|'onsite'|null,\n"
            "  availability_days: integer|null,\n"
            "  immediate: boolean|null,\n"
            "  top_n: integer|null,                 -- desired number of results\n"
            "  sort_by: 'relevance'|'experience'|'recency'|null,\n"
            "  extras: string[]                     -- other useful tokens\n"
            "}\n"
            "All arrays and strings must be lower-case; do not guess facts—use null/[] when absent."
        )
        user = query.strip()

        # Use the same client/model configured in chat_service
        client = chat_service.client
        model = chat_service.CHAT_MODEL

        if hasattr(client, "chat_completions"):
            chat = client.chat_completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
        else:
            chat = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0,
            )
        text = chat.choices[0].message.content or "{}"
        return json.loads(text)
    except Exception as e:
        try:
            logger.debug("intent_service LLM parse failed: %s", e)
        except Exception:
            pass
        return None


def parse_criteria_llm(query: str) -> Dict[str, Any]:
    """Parse user criteria. Prefer one LLM call, with a safe regex fallback."""
    data = _llm_parse(query)
    if not isinstance(data, dict):
        data = {}
    # Normalize and guard fields
    include = [str(x).lower() for x in data.get("include_skills", []) if isinstance(x, (str, int))]
    required = [str(x).lower() for x in data.get("required_skills", []) if isinstance(x, (str, int))]
    optional = [str(x).lower() for x in data.get("optional_skills", []) if isinstance(x, (str, int))]
    exclude = [str(x).lower() for x in data.get("exclude_skills", []) if isinstance(x, (str, int))]
    locations = [str(x).lower() for x in data.get("locations", []) if isinstance(x, (str, int))]
    titles = [str(x).lower() for x in data.get("titles", []) if isinstance(x, (str, int))]
    seniority = [str(x).lower() for x in data.get("seniority_levels", []) if isinstance(x, (str, int))]
    domains = [str(x).lower() for x in data.get("domains", []) if isinstance(x, (str, int))]
    extras = [str(x).lower() for x in data.get("extras", []) if isinstance(x, (str, int))]
    min_years = data.get("min_years") if isinstance(data.get("min_years"), int) else None
    max_years = data.get("max_years") if isinstance(data.get("max_years"), int) else None
    recent_years = data.get("recent_years") if isinstance(data.get("recent_years"), int) else None
    must_only = bool(data.get("must_only"))
    require_all = bool(data.get("require_all"))
    remote_mode = data.get("remote_mode") if isinstance(data.get("remote_mode"), str) else None
    availability_days = data.get("availability_days") if isinstance(data.get("availability_days"), int) else None
    immediate = bool(data.get("immediate")) if data.get("immediate") is not None else None
    top_n = data.get("top_n") if isinstance(data.get("top_n"), int) else None
    sort_by = data.get("sort_by") if isinstance(data.get("sort_by"), str) else None

    # Heuristic skill capture if LLM missed obvious tokens
    heuristic_skills = _heuristic_skills_from_query(query)
    if heuristic_skills and not include and not required:
        include = heuristic_skills
    elif heuristic_skills:
        for skill in heuristic_skills:
            if skill not in include:
                include.append(skill)

    if not include and not required:
        inferred_keywords = _llm_keywords_from_query(query)
        if inferred_keywords:
            include = inferred_keywords
            extras.extend(inferred_keywords)

    extras = list(dict.fromkeys([x for x in extras if x]))

    # If all empty, fallback
    # If parsing yields nothing, return an empty-but-valid structure; ranking will rely on vectors alone.
    if not any([include, required, optional, exclude, locations, titles, seniority, domains, extras, min_years, max_years, recent_years, must_only, require_all, remote_mode, availability_days, immediate, top_n, sort_by]):
        return {
            "include_skills": [],
            "required_skills": [],
            "optional_skills": [],
            "exclude_skills": [],
            "require_all": False,
            "must_only": False,
            "min_years": None,
            "max_years": None,
            "recent_years": None,
            "locations": [],
            "titles": [],
            "seniority_levels": [],
            "domains": [],
            "remote_mode": None,
            "availability_days": None,
            "immediate": None,
            "top_n": None,
            "sort_by": None,
            "extras": [],
            "raw_query": query.strip(),
        }

    return {
        "include_skills": include,
        "required_skills": required,
        "optional_skills": optional,
        "exclude_skills": exclude,
        "require_all": require_all,
        "must_only": must_only,
        "min_years": min_years,
        "max_years": max_years,
        "recent_years": recent_years,
        "locations": locations,
        "titles": titles,
        "seniority_levels": seniority,
        "domains": domains,
        "remote_mode": remote_mode,
        "availability_days": availability_days,
        "immediate": immediate,
        "top_n": top_n,
        "sort_by": sort_by,
        "extras": extras[:8],
        "raw_query": query.strip(),
    }


def rewrite_query(criteria: Dict[str, Any]) -> str:
    """Expand skills with synonyms and build a richer retrieval string."""
    inc = list(dict.fromkeys(criteria.get("include_skills", []) or []))
    req = list(dict.fromkeys(criteria.get("required_skills", []) or []))
    opt = list(dict.fromkeys(criteria.get("optional_skills", []) or []))
    exc = list(dict.fromkeys(criteria.get("exclude_skills", []) or []))
    locs = list(dict.fromkeys(criteria.get("locations", []) or []))
    titles = list(dict.fromkeys(criteria.get("titles", []) or []))
    seniority = list(dict.fromkeys(criteria.get("seniority_levels", []) or []))
    domains = list(dict.fromkeys(criteria.get("domains", []) or []))
    extras = list(dict.fromkeys(criteria.get("extras", []) or []))
    min_years = criteria.get("min_years")
    recent_years = criteria.get("recent_years")
    must_only = bool(criteria.get("must_only"))
    raw_query = str(criteria.get("raw_query") or "").strip()

    skill_terms: List[str] = []
    for s in inc:
        syns = _SYNONYMS.get(s, [s])
        skill_terms.extend(syns)
    # de-dup and keep concise
    skill_terms = list(dict.fromkeys(skill_terms))[:8]

    parts: List[str] = []
    if req:
        parts.append("required: " + ", ".join(req))
    if opt:
        parts.append("optional: " + ", ".join(opt))
    if skill_terms:
        parts.append("skills: " + ", ".join(skill_terms))
    if exc:
        parts.append("excluded: " + ", ".join(exc))
    if locs:
        parts.append("locations: " + ", ".join(locs))
    if min_years is not None:
        parts.append(f"TotalExperienceYears: >= {min_years}")
    if isinstance(recent_years, int) and recent_years > 0:
        parts.append(f"recent experience window: {recent_years} years")
    if must_only and inc:
        parts.append("primary language only: " + ", ".join(inc))
    if titles:
        parts.append("titles: " + ", ".join(titles))
    if seniority:
        parts.append("seniority: " + ", ".join(seniority))
    if domains:
        parts.append("domains: " + ", ".join(domains))
    if extras:
        parts.append("extras: " + ", ".join(extras[:6]))
    if raw_query:
        parts.append("query: " + raw_query)

    # Keep a compact, natural query string to guide retrieval
    query = " | ".join(parts) if parts else ""
    return query or raw_query or "relevant experience and skills"
