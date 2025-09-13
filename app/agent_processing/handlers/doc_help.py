from typing import Optional, List
from ..base import AgentHandler, AgentContext, AgentResult
from ..common import run_agent, session_append_ai, session_append_user
from app.core.config import settings
import os


def _get_known_files() -> List[str]:
    try:
        up = settings.UPLOAD_DIR
        if not os.path.isdir(up):
            return []
        allowed = {".pdf", ".csv", ".txt", ".md"}
        files = [f for f in os.listdir(up) if os.path.isfile(os.path.join(up, f))]
        return [f for f in files if os.path.splitext(f)[1].lower() in allowed]
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

        # Run the selected agent (DocHelp or similarly configured)
        output = run_agent(
            agent_name=ctx.agent_name,
            input_text=ctx.input_text,
            extra_tools=ctx.extra_tools,
            session_id=ctx.session_id,
        )
        session_append_ai(ctx.session_id, output if isinstance(output, str) else str(output))
        return AgentResult(response=output, session_id=ctx.session_id)
