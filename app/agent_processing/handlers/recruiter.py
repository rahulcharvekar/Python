from __future__ import annotations

import json
from typing import List

from ..base import AgentHandler, AgentContext, AgentResult
from ..common import run_agent
from app.services.generic import ingestion_db


class RecruiterHandler(AgentHandler):
    def handle(self, ctx: AgentContext) -> AgentResult:
        description = (ctx.input_text or "").strip()
        if not description:
            return AgentResult(
                response={"error": "Job description is required."},
                session_id=ctx.session_id,
                files=[],
            )

        try:
            records = ingestion_db.list_documents(ctx.agent_name)
        except Exception:
            records = []

        if not records:
            message = (
                "No candidate documents are available. Upload resumes for the recruiter agent and try again."
            )
            return AgentResult(response={"error": message}, session_id=ctx.session_id, files=[])

        files_for_agent = []
        for record in records:
            file_name = record.get("file") if isinstance(record, dict) else None
            if isinstance(file_name, str):
                files_for_agent.append(file_name)

        example_files = ", ".join(files_for_agent[:5])
        if len(files_for_agent) > 5:
            example_files += " ..."

        agent_output = run_agent(
            agent_name=ctx.agent_name,
            input_text=description,
            extra_tools=ctx.extra_tools,
            session_id=ctx.session_id,
            prompt_vars={
                "candidate_count": str(len(files_for_agent)),
                "candidate_files": example_files or "none",
            },
        )

        response_text = agent_output if isinstance(agent_output, str) else str(agent_output)

        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError:
            payload = {
                "matches": [],
                "message": "Unable to parse agent response as JSON.",
                "raw_response": response_text,
            }

        matches = payload.get("matches") if isinstance(payload, dict) else None
        files: List[str] = []
        if isinstance(matches, list):
            for item in matches:
                if isinstance(item, dict):
                    file_name = item.get("file")
                    if isinstance(file_name, str):
                        files.append(file_name)

        return AgentResult(response=payload, session_id=ctx.session_id, files=files)
