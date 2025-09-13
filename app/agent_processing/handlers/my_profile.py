from app.core.config import settings
from ..base import AgentHandler, AgentContext, AgentResult
from ..common import run_agent, session_append_ai, session_append_user


class MyProfileHandler(AgentHandler):
    def handle(self, ctx: AgentContext) -> AgentResult:
        # Config check
        if not settings.MYPROFILE_FILE:
            msg = (
                "MyProfile is not configured. Set MYPROFILE_FILE to an absolute path (e.g., /PYTHON/app/profile.md) "
                "or place the file under uploads."
            )
            session_append_user(ctx.session_id, ctx.input_text)
            session_append_ai(ctx.session_id, msg)
            return AgentResult(response=msg, session_id=ctx.session_id)

        # No guardrails for file intent; proceed to run agent
        output = run_agent(
            agent_name=ctx.agent_name,
            input_text=ctx.input_text,
            extra_tools=ctx.extra_tools,
            session_id=ctx.session_id,
            prompt_vars={
                "profile_file": settings.MYPROFILE_FILE or "<UNCONFIGURED>",
            },
        )
        session_append_ai(ctx.session_id, output if isinstance(output, str) else str(output))
        return AgentResult(response=output, session_id=ctx.session_id)
