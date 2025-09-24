from __future__ import annotations

import os
from typing import List

from app.core.config import settings
from ..base import AgentHandler, AgentContext, AgentResult
from ..common import run_agent, session_append_ai, session_append_user
from app.services.generic import ingestion_db
from app.services.agents import recruiter_service


def _allowed_files_for_recruiter() -> List[str]:
    allowed_ext = {".pdf", ".txt", ".md", ".docx", ".doc"}
    try:
        rows = ingestion_db.list_documents("Recruiter")
        files: List[str] = []
        for r in rows:
            fn = r.get("file") if isinstance(r, dict) else None
            if isinstance(fn, str) and os.path.splitext(fn)[1].lower() in allowed_ext:
                files.append(fn)
        return files
    except Exception:
        return []


class RecruiterHandler(AgentHandler):
    def handle(self, ctx: AgentContext) -> AgentResult:
        text = (ctx.input_text or "").strip()
        
        # Intercept slash commands
        lowered = text.lower()
        
        # Slash commands removed; handler processes queries directly

        # Deprecated: explicit /searchprofilellm command; plain queries trigger intent search when no file is selected

        # Normal query path: intent-filter first, then answer with the best-matching resume
        files = _allowed_files_for_recruiter()
        if not files:
            msg = (
                "No resumes available. Upload resumes with agent=Recruiter, then try again."
            )
            session_append_user(ctx.session_id, ctx.input_text)
            session_append_ai(ctx.session_id, msg)
            return AgentResult(response=msg, session_id=ctx.session_id)

        # 1) Run intent parsing + shortlist for every recruiter query
        shortlist = recruiter_service.search_profiles_intent_llm(text, agent="Recruiter")

        # 2) If filename provided in payload, use it; otherwise return shortlist (no auto-select)
        if ctx.file_override:
            if ctx.file_override not in files:
                options = ", ".join(files[:10]) + (" …" if len(files) > 10 else "")
                msg = (
                    f"File not found: {ctx.file_override}. Use an exact filename." +
                    (f" Options: {options}" if options else "")
                )
                session_append_user(ctx.session_id, ctx.input_text)
                session_append_ai(ctx.session_id, msg)
                return AgentResult(response=msg, session_id=ctx.session_id)
            active_file = ctx.file_override
        else:
            if not shortlist:
                msg = "No matching profiles found."
            else:
                lines = [
                    f"- {r.get('file')} (score={r.get('best_score')})" + (f" — {r.get('name')}" if r.get('name') else "")
                    for r in shortlist[:10]
                ]
                msg = "Top matches (LLM intent + vectors):\n" + "\n".join(lines)
            session_append_user(ctx.session_id, ctx.input_text)
            session_append_ai(ctx.session_id, msg)
            return AgentResult(response=msg, session_id=ctx.session_id)

        # 4) Answer using the resolved resume
        input_text = ctx.input_text
        if active_file:
            input_text = f"Use file '{active_file}' for all tool calls in this session. " + (ctx.input_text or "")
        output = run_agent(
            agent_name=ctx.agent_name,
            input_text=input_text,
            extra_tools=ctx.extra_tools,
            session_id=ctx.session_id,
            prompt_vars={
                "doc_file": active_file,
            },
        )
        session_append_ai(ctx.session_id, output if isinstance(output, str) else str(output))
        return AgentResult(response=output, session_id=ctx.session_id)
