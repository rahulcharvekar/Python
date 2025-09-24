from typing import Optional, List
from ..base import AgentHandler, AgentContext, AgentResult
from ..common import run_agent, session_append_ai, session_append_user
from app.agents.session_memory import SessionMemory
from app.core.config import settings
import os
from app.services.generic import ingestion_db


def _get_known_files() -> List[str]:
    """Return files known for DocHelp from SQLite (ingestion_db)."""
    try:
        allowed = {".pdf", ".csv", ".txt", ".md", ".docx", ".doc"}
        rows = ingestion_db.list_documents("DocHelp")
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
            session_append_user(ctx.session_id, ctx.input_text)
            session_append_ai(ctx.session_id, msg)
            return AgentResult(response=msg, session_id=ctx.session_id)

        # Filename override via API payload: pin to session and use directly
        active_key = "active_file:DocHelp"
        active_file = None
        if ctx.file_override:
            if ctx.file_override in known_files:
                active_file = ctx.file_override
                if ctx.session_id:
                    SessionMemory.set_kv(ctx.session_id, active_key, active_file)
            else:
                options = ", ".join(known_files[:10]) + (" …" if len(known_files) > 10 else "")
                msg = (
                    f"File not found: {ctx.file_override}. Please provide an exact filename." +
                    (f" Options: {options}" if options else "")
                )
                session_append_user(ctx.session_id, ctx.input_text)
                session_append_ai(ctx.session_id, msg)
                return AgentResult(response=msg, session_id=ctx.session_id)

        # Session-pinned file selection for DocHelp (fallback when no override)
        if not active_file:
            active_file = SessionMemory.get_kv(ctx.session_id or "", active_key) if ctx.session_id else None

        # If user mentions a known filename explicitly, pin it
        lowered = (ctx.input_text or "").lower()
        mentioned = None
        for f in known_files:
            if f.lower() in lowered:
                mentioned = f
                break
        if mentioned and ctx.session_id:
            SessionMemory.set_kv(ctx.session_id, active_key, mentioned)
            active_file = mentioned

        # If still no active file: auto-select if only one, else ask user to choose
        if not active_file:
            if len(known_files) == 1:
                active_file = known_files[0]
                if ctx.session_id:
                    SessionMemory.set_kv(ctx.session_id, active_key, active_file)
            else:
                options = ", ".join(known_files[:10]) + (" …" if len(known_files) > 10 else "")
                msg = f"Multiple files are available for this agent. Please provide 'filename' in the request or reply with the exact filename to use. Options: {options}"
                session_append_user(ctx.session_id, ctx.input_text)
                session_append_ai(ctx.session_id, msg)
                return AgentResult(response=msg, session_id=ctx.session_id)

        # Run the selected agent (DocHelp or similarly configured)
        input_text = ctx.input_text
        if active_file:
            # Keep a soft hint in the input, and also pass explicit prompt vars
            input_text = f"Use file '{active_file}' for all tool calls in this session. " + (ctx.input_text or "")
        output = run_agent(
            agent_name=ctx.agent_name,
            input_text=input_text,
            extra_tools=ctx.extra_tools,
            session_id=ctx.session_id,
            prompt_vars={"doc_file": active_file} if active_file else None,
        )
        session_append_ai(ctx.session_id, output if isinstance(output, str) else str(output))
        return AgentResult(response=output, session_id=ctx.session_id)
