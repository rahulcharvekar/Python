from __future__ import annotations

import re
from typing import Iterable, List, Set


_DEFAULT_STOPWORDS: Set[str] = {
    "and", "or", "the", "a", "an", "is", "are", "with", "in", "of", "to", "for", "on", "at", "by", "as", "be",
    "this", "that", "it", "from", "was", "were", "am", "i", "we", "you", "they", "he", "she", "have", "has", "had",
    "my", "our", "their", "your", "over", "using", "use", "used", "etc", "pdf", "doc", "docx", "txt", "resume", "cv",
    "csv", "xlsx", "md", "file", "document",
}


def extract_keywords(
    text: str,
    *,
    max_k: int = 40,
    stopwords: Iterable[str] | None = None,
) -> List[str]:
    """Extract frequent lowercase keywords from free-form text."""
    stop = set(stopwords or []) | _DEFAULT_STOPWORDS
    cleaned = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    tokens = [t for t in cleaned.split() if t]
    counts: dict[str, int] = {}
    for token in tokens:
        if token in stop or len(token) < 2:
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [term for term, _ in ranked[:max_k]]
