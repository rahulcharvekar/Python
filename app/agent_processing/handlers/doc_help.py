from typing import List
from ..base import AgentHandler, AgentContext, AgentResult
from ..common import run_agent
import os
from app.services.generic import ingestion_db


def _get_known_files() -> List[str]:
    """Return files known for DocHelp from SQLite (ingestion_db)."""
    try:
        allowed = {".pdf", ".csv", ".txt", ".md", ".docx", ".doc"}
        rows = ingestion_db.list_documents("dochelp")
        files = [r.get("file") for r in rows if isinstance(r, dict)]
        return [f for f in files if isinstance(f, str) and os.path.splitext(f)[1].lower() in allowed]
    except Exception:
        return []


class DocHelpHandler(AgentHandler):
    def handle(self, ctx: AgentContext) -> AgentResult:
        known_files = _get_known_files()
        # Minimal guard: avoid LLM call when no files available
        if not known_files:
            msg = (
                "This assistant answers questions grounded in uploaded files. "
                "Please upload a file and ask your question about it."
            )
            return AgentResult(response=msg, session_id=ctx.session_id, files=[])

        active_file = None

        override = (ctx.filename or "").strip()
        if override:
            if override in known_files:
                active_file = override
            else:
                options = ", ".join(known_files[:10]) + (" …" if len(known_files) > 10 else "")
                msg = (
                    f"File not found: {override}. Please provide an exact filename."
                    + (f" Options: {options}" if options else "")
                )
                return AgentResult(response=msg, session_id=ctx.session_id, files=[])

        if not active_file:
            lowered = (ctx.input_text or "").lower()
            for f in known_files:
                if f.lower() in lowered:
                    active_file = f
                    break

        # Require explicit file selection before running the agent
        if not active_file:
            if len(known_files) == 1:
                active_file = known_files[0]
            else:
                options = ", ".join(known_files[:10]) + (" …" if len(known_files) > 10 else "")
                msg = (
                    "Please specify which uploaded file to use before continuing. "
                    + (f"Options: {options}" if options else "No files found in storage.")
                )

                return AgentResult(response=msg, session_id=ctx.session_id, files=[])

        output = run_agent(
            agent_name=ctx.agent_name,
            input_text=ctx.input_text,
            extra_tools=ctx.extra_tools,
            session_id=ctx.session_id,
            prompt_vars={"doc_file": active_file} if active_file else None,
        )

        response_text = output if isinstance(output, str) else str(output)
        return AgentResult(response=response_text, session_id=ctx.session_id, files=[])
