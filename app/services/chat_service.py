# rag_core.py — Query via LangChain's Chroma (normalized scores + robust fallback)

from textwrap import dedent
from pathlib import Path
from typing import List, Tuple, Dict, Any

from openai import OpenAI
from app.utils.Logging.logger import logger
from app.core.config import settings

# LangChain vector store + embeddings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from app.utils.fileops.fileutils import hash_file


# -------------------------------
# Build OpenAI-compatible client
# -------------------------------
def _get_client_and_model():
    app_env = settings.APP_ENV.lower()
    if app_env == "development":
        client = OpenAI(
            api_key=getattr(settings, "LOCAL_LLM_API_KEY", None),
            base_url=getattr(settings, "LOCAL_LLM_BASE_URL", None),
        )
        model = settings.LOCAL_LLM_MODEL
        return client, model
    else:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required in production.")
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        model = settings.OPENAI_MODEL
        return client, model


client, CHAT_MODEL = _get_client_and_model()


# -------------------------------
# Embedding fn (must match ingestion)
# -------------------------------
def _get_embedding_fn():
    """
    IMPORTANT: Use the same embedding model as ingestion.
    Defaults to text-embedding-3-small if OPENAI_EMBEDDING_MODEL not set.
    """
    app_env = settings.APP_ENV.lower()
    if app_env == "development":
        return HuggingFaceEmbeddings(model_name=settings.HUGGINGFACE_EMBEDDING_MODEL)
    return OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_EMBEDDING_MODEL)


# -------------------------------
# Vector store (LangChain-Chroma)
# -------------------------------
def _collection_name_from(file: str) -> str:
    # Derive a unique, content-based name matching ingestion logic.
    stem = Path(file).stem
    file_path = Path(settings.UPLOAD_DIR) / file
    try:
        h = hash_file(file_path)
        return f"{stem}-{h[:12]}"
    except Exception:
        # Fallback to stem if file missing; avoids hard failure during testing
        return stem


def _get_vectorstore(collection_name: str) -> Chroma:
    persist_dir = Path(settings.CHROMA_DIR)
    vs = Chroma(
        collection_name=collection_name,
        persist_directory=str(persist_dir),
        embedding_function=_get_embedding_fn(),
    )
    logger.info("Chroma loaded | dir=%s | collection=%s", persist_dir, collection_name)
    try:
        cnt = vs._collection.count()  # type: ignore[attr-defined]
        logger.info("Collection '%s' vector count: %s", collection_name, cnt)
    except Exception as e:
        logger.debug("Vector count unavailable: %s", e)
    return vs


# -------------------------------
# Score normalization helpers
# -------------------------------
def _normalize_scores(raw_scores: List[float]) -> List[float]:
    """
    Normalize whatever the backend returns into [0, 1] relevance scores (higher=better).

    Heuristics:
      - If any score < 0.0 → assume cosine similarity in [-1, 1], map: s_norm = (s + 1) / 2
      - Else if any score > 1.0 → assume distance in [0, 2] (cosine distance), map: s_norm = 1 - min(s/2, 1)
      - Else → already in [0,1]
    """
    if not raw_scores:
        return raw_scores

    mn, mx = min(raw_scores), max(raw_scores)

    if mn < 0.0:
        # Likely cosine similarity in [-1,1]
        return [max(0.0, min(1.0, (s + 1.0) / 2.0)) for s in raw_scores]

    if mx > 1.0:
        # Likely distance in [0,2] (smaller=better)
        return [max(0.0, 1.0 - min(s / 2.0, 1.0)) for s in raw_scores]

    # Already 0..1
    return raw_scores


# -------------------------------
# Retrieval (normalize + threshold + fallback)
# -------------------------------
def retrieve(
    file: str,
    query: str,
    k: int = 8,
    score_threshold: float = 0.62,
) -> List[Tuple[str, Dict[str, Any], float]]:
    """
    Returns [(doc_text, metadata, norm_score)], norm_score in [0,1], higher is better.
    Applies a threshold and sorts by score desc. If nothing passes threshold,
    falls back to the top-k (by normalized score) to avoid empty context.
    """
    collection = _collection_name_from(file)
    logger.info(
        "Retrieving | dir=%s | collection=%s | k=%s | threshold=%.2f",
        settings.CHROMA_DIR, collection, k, score_threshold,
    )

    vs = _get_vectorstore(collection)
    pairs = vs.similarity_search_with_relevance_scores(query, k=k)  # [(Document, raw_score)]

    docs = [doc for (doc, _s) in pairs]
    raw_scores = [float(s) for (_d, s) in pairs]

    # Normalize to [0,1] regardless of backend semantics
    norm_scores = _normalize_scores(raw_scores)

    results: List[Tuple[str, Dict[str, Any], float]] = []
    for doc, ns in zip(docs, norm_scores):
        results.append((doc.page_content or "", (doc.metadata or {}), ns))

    # Best-first ordering
    results.sort(key=lambda x: x[2], reverse=True)

    # Apply threshold
    filtered = [r for r in results if r[2] >= score_threshold]

    # If nothing meets the bar, fall back to top-k normalized results (still sorted best-first)
    final_hits = filtered if filtered else results[:k]

    logger.info(
        "Top hits (post-normalization)%s: %s",
        "" if filtered else " [FALLBACK: below threshold]",
        [
            {"score": round(s, 3), "source": (m.get("source") if isinstance(m, dict) else None)}
            for _, m, s in final_hits[:5]
        ],
    )

    return final_hits


# -------------------------------
# Prompt building (context first + truncation guard)
# -------------------------------
def _shrink_blocks(hits, max_chars: int = 6000):
    total = 0
    kept = []
    for (doc, meta, score) in hits:
        block = (doc or "").strip()
        if not block:
            continue
        if total + len(block) > max_chars:
            remain = max_chars - total
            if remain > 400:  # keep a meaningful tail
                kept.append((block[:remain], meta, score))
            break
        kept.append((block, meta, score))
        total += len(block)
    return kept


def build_prompt(query: str, hits) -> str:
    hits = _shrink_blocks(hits, max_chars=6000)

    if not hits:
        context = "No strong matches were retrieved for this query."
    else:
        blocks = []
        for i, (doc, meta, score) in enumerate(hits, start=1):
            tag_src = meta.get("source") if isinstance(meta, dict) else None
            tag_pg = meta.get("page") if isinstance(meta, dict) else None
            tags = []
            if tag_src: tags.append(f"source={tag_src}")
            if tag_pg is not None: tags.append(f"page={tag_pg}")
            tags.append(f"score={round(score, 3)}")
            header = f"[{i}] " + " | ".join(tags)
            blocks.append(f"{header}\n{doc}\n")
        context = "\n\n".join(blocks)

    prompt = dedent(f"""
    You must answer using ONLY the context blocks. If the answer is not present, reply exactly:
    "I don't know based on the provided context."

    # Context
    {context}

    # Question
    {query}

    # Answering rules
    - If you used info from blocks, cite them like [1], [2].
    - Be concise and factual. Do not speculate beyond the context.
    """).strip()

    return prompt


# -------------------------------
# Orchestration
# -------------------------------
def answer(file: str, query: str, k: int = 8) -> dict:
    hits = retrieve(file, query, k=k, score_threshold=0.62)
    logger.info("Answering query: %s | hits_used=%d", query, len(hits))

    prompt = build_prompt(query, hits)

    # Use the new endpoint if available; fallback for older client variants
    if hasattr(client, "chat_completions"):
        chat = client.chat_completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You only use provided context. No outside knowledge."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
    else:
        chat = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You only use provided context. No outside knowledge."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

    text = chat.choices[0].message.content
    return {"response": text}


def plain_chat(query: str) -> dict:
    """
    Basic, non-contextual chat using the configured chat model.
    Returns a dict with key "response" for consistency with answer().
    """
    # Use the new endpoint if available; fallback for older client variants
    if hasattr(client, "chat_completions"):
        chat = client.chat_completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query},
            ],
            temperature=0.2,
        )
    else:
        chat = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query},
            ],
            temperature=0.2,
        )

    text = chat.choices[0].message.content
    return {"response": text}
