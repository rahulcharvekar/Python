# rag_core.py
import os
import chromadb
from openai import OpenAI
from textwrap import dedent

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]  # set in your env
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "my_docs")

client = OpenAI(api_key=OPENAI_API_KEY)
chroma_client = chromadb.PersistentClient(path=os.getenv("CHROMA_DIR", "./chroma"))
collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION)

def retrieve(query: str, k: int = 4):
    """
    If your collection stores embeddings, Chroma can handle text queries directly.
    Returns [(doc_text, metadata, distance), ...]
    """
    res = collection.query(query_texts=[query], n_results=k, include=["documents", "metadatas", "distances"])
    docs = res["documents"][0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    return list(zip(docs, metas, dists))

def build_prompt(query: str, hits) -> str:
    context_blocks = []
    for i, (doc, meta, dist) in enumerate(hits, start=1):
        src = meta.get("source") if isinstance(meta, dict) else None
        tag = f" [source: {src}]" if src else ""
        context_blocks.append(f"[{i}]{tag}\n{doc}\n")
    context = "\n\n".join(context_blocks)

    prompt = dedent(f"""
    You are a helpful assistant. Answer the user's question using ONLY the context below.
    If the answer is not in the context, say you don't know.

    # User question
    {query}

    # Context
    {context}

    # Instructions
    - Always cite the block numbers you used, like [1], [2].
    - Be concise.
    """).strip()
    return prompt

def answer(query: str, k: int = 4) -> dict:
    hits = retrieve(query, k=k)
    prompt = build_prompt(query, hits)

    # Responses API (modern) call
    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=[{"role": "user", "content": prompt}],
    )

    text = resp.output_text  # single string convenience
    # You may also want to return top sources for UI highlighting
    sources = [{"idx": i+1, "meta": m, "distance": d} for i, (_, m, d) in enumerate(hits)]
    return {"response": text, "sources": sources}
