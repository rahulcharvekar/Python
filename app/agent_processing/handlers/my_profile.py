from app.core.config import settings
from ..base import AgentHandler, AgentContext, AgentResult
from ..common import run_agent, session_append_ai, session_append_user
from pathlib import Path
import re
from app.utils.Logging.logger import logger


def _resolve_profile_path(profile_file: str) -> Path:
    """Best-effort resolution of the profile file path.
    Tries absolute path first; otherwise resolves under uploads dir.
    """
    p = Path(profile_file)
    if p.is_absolute() and p.exists():
        return p
    # Try relative to configured UPLOAD_DIR
    up = Path(settings.UPLOAD_DIR) / profile_file
    if up.exists():
        return up
    # Fallback: return as-is (may not exist, used only for display)
    return p


def _extract_profile_name(profile_path: Path) -> str | None:
    """Extract a human name from a markdown/txt profile.
    Heuristics: first markdown heading, then 'Name: ...' line, else derive from filename.
    """
    try:
        if profile_path.exists() and profile_path.suffix.lower() in {".md", ".txt"}:
            text = profile_path.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith("#"):
                    return s.lstrip("# ").strip()
            # Name: pattern
            m = re.search(r"^\s*name\s*[:\-]\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
            if m:
                return m.group(1).strip()
        # Derive from filename if readable
        stem = profile_path.stem
        if stem and any(c.isalpha() for c in stem):
            pretty = re.sub(r"[_\-]+", " ", stem).strip().title()
            if pretty and pretty.lower() != "profile":
                return pretty
    except Exception:
        pass
    return None


def _rewrite_pronouns_to_name(text: str, name: str) -> str:
    """Rewrite second-person pronouns to the provided name.
    Examples: 'your' -> "Rahul Charvekar's", 'you' -> 'Rahul Charvekar', 'yourself' -> 'Rahul Charvekar'.
    Conservative, whole-word replacements.
    """
    if not text or not name:
        return text
    repl = text
    # Order matters: handle longer tokens first
    repl = re.sub(r"\byourself\b", name, repl, flags=re.IGNORECASE)
    repl = re.sub(r"\byours\b", f"{name}'s", repl, flags=re.IGNORECASE)
    repl = re.sub(r"\byour\b", f"{name}'s", repl, flags=re.IGNORECASE)
    repl = re.sub(r"\bur\b", f"{name}'s", repl, flags=re.IGNORECASE)  # common shorthand
    repl = re.sub(r"\byou\b", name, repl, flags=re.IGNORECASE)
    repl = re.sub(r"\bu\b", name, repl, flags=re.IGNORECASE)  # shorthand
    return repl


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

        # Resolve profile path and try to infer the profile owner's name
        profile_path = _resolve_profile_path(settings.MYPROFILE_FILE)
        profile_name = _extract_profile_name(profile_path) or "the profile owner"
        logger.info(f"profile_path {profile_path}")
        logger.info(f"profile_name {profile_name}")
        # Rewrite second-person pronouns to the profile owner's name
        rewritten_input = _rewrite_pronouns_to_name(ctx.input_text or "", profile_name if profile_name != "the profile owner" else "")

        # No guardrails for file intent; proceed to run agent
        output = run_agent(
            agent_name=ctx.agent_name,
            input_text=rewritten_input or ctx.input_text,
            extra_tools=ctx.extra_tools,
            session_id=ctx.session_id,
            prompt_vars={
                "profile_file": settings.MYPROFILE_FILE or "<UNCONFIGURED>",
                "profile_name": profile_name,
            },
        )
        session_append_ai(ctx.session_id, output if isinstance(output, str) else str(output))
        return AgentResult(response=output, session_id=ctx.session_id)
