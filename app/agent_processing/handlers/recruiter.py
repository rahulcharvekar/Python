from __future__ import annotations

import os
from typing import List

from app.core.config import settings
from ..base import AgentHandler, AgentContext, AgentResult
from ..common import run_agent, session_append_ai, session_append_user
from app.services.generic import ingestion_db
from app.agents.session_memory import SessionMemory
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
        
        if lowered.startswith("/listfiles"):
            # Show files with optional name/skills/keywords if available
            try:
                rows = recruiter_service.list_indexed_profiles(agent="Recruiter")
            except Exception:
                rows = []
            allowed_ext = {".pdf", ".txt", ".md", ".docx", ".doc"}
            display_rows = []
            for r in rows:
                f = r.get("file")
                if not isinstance(f, str):
                    continue
                _, ext = os.path.splitext(f)
                if ext.lower() not in allowed_ext:
                    continue
                name = r.get("name") or ""
                skills = (r.get("skills") or "").strip()
                kw = (r.get("keywords") or "").split()
                kw_short = " ".join(kw[:12]) if kw else ""
                parts = [f"- {f}"]
                if name:
                    parts.append(f"— {name}")
                if skills:
                    parts.append(f"— skills: {skills}")
                if kw_short:
                    parts.append(f"— kw: {kw_short}")
                display_rows.append(" ".join(parts))

            if not display_rows:
                msg = "No resumes found. Upload files with agent=Recruiter, then try again."
            else:
                msg = "\n".join(display_rows[:10]) + (" …" if len(display_rows) > 10 else "")
            session_append_user(ctx.session_id, ctx.input_text)
            session_append_ai(ctx.session_id, msg)
            return AgentResult(response=msg, session_id=ctx.session_id)

        if lowered.startswith("/selectresume"):
            parts = text.split(maxsplit=1)
            files = _allowed_files_for_recruiter()
            options = ", ".join(files[:10]) + (" …" if len(files) > 10 else "")
            if len(parts) < 2:
                msg = (
                    "No resume selected. Use /selectresume <filename> to select one." +
                    (f" Options: {options}" if options else "")
                )
            else:
                filename = parts[1].strip()
                if filename in files:
                    if ctx.session_id:
                        SessionMemory.set_kv(ctx.session_id, "active_file:Recruiter", filename)
                    msg = f"Selected resume: {filename}. You can now ask questions."
                else:
                    msg = (
                        f"File not found: {filename}. Use /selectresume <filename> with an exact name." +
                        (f" Options: {options}" if options else "")
                    )
            session_append_user(ctx.session_id, ctx.input_text)
            session_append_ai(ctx.session_id, msg)
            return AgentResult(response=msg, session_id=ctx.session_id)

        if lowered.startswith("/searchprofilellm"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                msg = "Usage: /searchprofilellm <llm query>"   
            else:
                query = parts[1].strip()
                results = recruiter_service.search_profiles(query, agent="Recruiter")
                if not results:
                    msg = "No matching profiles found."
                else:
                    lines = [
                        f"- {r.get('file')} (score={r.get('best_score')})" + (f" — {r.get('name')}" if r.get('name') else "")
                        for r in results[:10]
                    ]
                    msg = "Top matches (LLM):\n" + "\n".join(lines)
            session_append_user(ctx.session_id, ctx.input_text)
            session_append_ai(ctx.session_id, msg)
            return AgentResult(response=msg, session_id=ctx.session_id)

        if lowered.startswith("/searchprofile"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                msg = "Usage: /searchprofile <keywords>"
            else:
                query = parts[1].strip()
                results = recruiter_service.search_profiles_keyword(query, agent="Recruiter")
                if not results:
                    msg = "No matching profiles found."
                else:
                    lines = [
                        f"- {r.get('file')} (score={r.get('best_score')})" + (f" — {r.get('name')}" if r.get('name') else "")
                        for r in results[:10]
                    ]
                    msg = "Top matches:\n" + "\n".join(lines)
            session_append_user(ctx.session_id, ctx.input_text)
            session_append_ai(ctx.session_id, msg)
            return AgentResult(response=msg, session_id=ctx.session_id)

        # Normal query path: ensure an active file is selected
        files = _allowed_files_for_recruiter()
        if not files:
            msg = (
                "No resumes available. Upload resumes with agent=Recruiter, then use /listfiles and /selectresume to choose one."
            )
            session_append_user(ctx.session_id, ctx.input_text)
            session_append_ai(ctx.session_id, msg)
            return AgentResult(response=msg, session_id=ctx.session_id)

        active_key = "active_file:Recruiter"
        active_file = SessionMemory.get_kv(ctx.session_id or "", active_key) if ctx.session_id else None

        # Require explicit selection even if only one file exists
        if not active_file:
            msg = (
                "Please select a resume using /selectresume <filename>. "
                "Use /listfiles to see available options."
            )
            session_append_user(ctx.session_id, ctx.input_text)
            session_append_ai(ctx.session_id, msg)
            return AgentResult(response=msg, session_id=ctx.session_id)

        # Delegate to the Recruiter agent with the selected file injected
        output = run_agent(
            agent_name=ctx.agent_name,
            input_text=ctx.input_text,
            extra_tools=ctx.extra_tools,
            session_id=ctx.session_id,
            prompt_vars={
                "doc_file": active_file,
            },
        )
        session_append_ai(ctx.session_id, output if isinstance(output, str) else str(output))
        return AgentResult(response=output, session_id=ctx.session_id)
