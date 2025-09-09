AI Assistant (FastAPI + RAG)

Overview
- FastAPI service that lets you upload PDFs/CSVs, indexes them in Chroma (vector DB), and answers questions grounded in those documents via an LLM.
- Embeddings are now aligned across ingestion and retrieval:
  - Development: HuggingFace embeddings (sentence-transformers/all-MiniLM-L6-v2)
  - Production: OpenAI embeddings (text-embedding-3-small by default)

Project Layout
- `main.py` — FastAPI app factory, CORS, include routers.
- `app/api/` — HTTP routes:
  - `POST /upload` — upload and register a file.
  - `GET  /upload/getall` — list registered files.
  - `POST /get_insights/{file}` — build embeddings/Chroma collection for a file.
  - `POST /chat/{file}/{query}` — query the file with retrieval-augmented generation.
- `app/workflow/` — request orchestration.
- `app/services/` — file upload, vector store build, retrieval + LLM chat.

## Agent + Tools Architecture

This repo now exposes services as LangChain tools and routes requests through agents. You can:

- Use `/agent/query` to send a natural-language instruction; the agent will decide which tool to call.
- Keep using existing endpoints; `chat` and `get_insights` are internally routed through the agent.

Key files:

- `app/tools/` — LangChain tool wrappers around existing services
  - `app/tools/chat_tools.py` — `chat_over_file(file, query)`
  - `app/tools/insight_tools.py` — `initialize_insights(file)`
  - `app/tools/registry_tools.py` — `list_files()`
  - `app/tools/__init__.py` — central tool registry (`ALL_TOOLS`, `get_tools_by_names`)
- `app/agents/` — agent wiring
  - `app/agents/config.py` — define multiple agents, their tools, and prompts
  - `app/agents/agent_factory.py` — build an AgentExecutor with selected tools
- `app/api/agent.py` — `/agent/query` and `/agent/list` endpoints

Add a tool:

1. Create a new file in `app/tools/` and define a function decorated with `@tool("your_tool_name")`.
2. Import and append your tool to `ALL_TOOLS` in `app/tools/__init__.py`.
3. Add the tool name to any agent in `app/agents/config.py`.

Add an agent:

1. Add a new entry in `app/agents/config.py` with a unique name, `tools` list, and `system_prompt`.
2. Call `/agent/query` with `{ "agent": "your_agent", "input": "..." }`.

Example requests:

```
POST /agent/query
{
  "input": "Initialize or update the vector index for file 'mydoc.pdf'"
}

POST /agent/query
{
  "input": "Answer using file 'mydoc.pdf': what are the payment terms?"
}
```
- `app/core/config.py` — central settings with sensible defaults.
- `uploads/`, `vector_store/`, `db_store/`, `logs/` — runtime storage.


Requirements
- Python 3.11+
- For development embeddings: no API keys needed (HuggingFace model downloaded automatically).
- For production embeddings and chat: OpenAI API key.

Quick Start (Local Dev)
1) Install deps
   - `python -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`

2) Environment (development uses local defaults)
   - Create `.env.local` if needed and set any overrides. Common options:
     - `APP_ENV=development`
     - Optional (for local chat via an OpenAI-compatible server like Ollama):
       - `LOCAL_LLM_BASE_URL=http://127.0.0.1:11434/v1`
       - `LOCAL_LLM_MODEL=llama3.1:8b-instruct`

3) Run the API
   - `uvicorn main:app --reload --port 8000`
   - CORS allows `http://localhost:5173` by default (see `main.py`).

Quick Start (Production)
- Set required environment variables (e.g., in `.env.local`):
  - `APP_ENV=production`
  - `OPENAI_API_KEY=<your key>`
  - `OPENAI_MODEL=gpt-4.1` (or preferred)
  - `OPENAI_EMBEDDING_MODEL=text-embedding-3-small` (or preferred)

Endpoints
- Upload a file
  - `POST /upload` (multipart form field name: `file`)
- List files
  - `GET /upload/getall`
- Build embeddings for a file
  - `POST /get_insights/{file}`
- Chat over a file
  - `POST /chat/{file}/{query}`

Embedding Alignment Details
- In development (`APP_ENV=development`):
  - Ingestion: `HuggingFaceEmbeddings(model_name=HUGGINGFACE_EMBEDDING_MODEL)`
  - Retrieval: same as ingestion.
- In production (`APP_ENV=production`):
  - Ingestion: `OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=OPENAI_API_KEY)`
  - Retrieval: same as ingestion.
- You can change default models via env vars in `app/core/config.py`:
  - `HUGGINGFACE_EMBEDDING_MODEL` (default: sentence-transformers/all-MiniLM-L6-v2)
  - `OPENAI_EMBEDDING_MODEL` (default: text-embedding-3-small)

Notes
- Ensure you call `POST /get_insights/{file}` after uploading to build the Chroma collection before chatting.
- Vector collections are named by file stem (filename without extension).
- The SQLite registry tracks uploads; its `vector_path` entry is informational.

Container & Deploy
- Dockerfile provided (Python 3.11-slim). Entry via `startup.sh`.
- GitHub Action deploys to Azure Web App (zip deploy).
