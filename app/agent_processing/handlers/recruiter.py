from __future__ import annotations

import json
from typing import List

from ..base import AgentHandler, AgentContext, AgentResult
from ..common import run_agent
from app.services.generic import ingestion_db
from app.services.agents import recruiter_service
from app.utils.Logging.logger import logger


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
            logger.info("Recruiter handler aborting: no documents indexed for agent '%s'", ctx.agent_name)
            return AgentResult(response={"error": message}, session_id=ctx.session_id, files=[])

        files_for_agent = []
        for record in records:
            file_name = record.get("file") if isinstance(record, dict) else None
            if isinstance(file_name, str):
                files_for_agent.append(file_name)

        file_override = (ctx.filename or "").strip()
        prompt_vars = {
            "candidate_count": str(len(files_for_agent)),
            "candidate_files": ", ".join(files_for_agent[:5]) + (" ..." if len(files_for_agent) > 5 else ""),
            "doc_file": "",
            "original_query": description,
        }

        if file_override:
            if file_override not in files_for_agent:
                options = ", ".join(files_for_agent[:10]) + (" ..." if len(files_for_agent) > 10 else "")
                message = (
                    f"File not found for recruiter agent: {file_override}."
                    + (f" Options: {options}" if options else "")
                )
                logger.warning(
                    "Recruiter handler received unknown file override | agent=%s | filename=%s",
                    ctx.agent_name,
                    file_override,
                )
                return AgentResult(response={"error": message}, session_id=ctx.session_id, files=[])

            prompt_vars["doc_file"] = file_override

        extra_tools = list(ctx.extra_tools or [])

        agent_output = run_agent(
            agent_name=ctx.agent_name,
            input_text=description,
            extra_tools=extra_tools,
            session_id=ctx.session_id,
            prompt_vars=prompt_vars,
        )

        response_text = agent_output if isinstance(agent_output, str) else str(agent_output)

        if file_override:
            logger.info(
                "Recruiter profile chat completed via tool routing | file=%s | session=%s",
                file_override,
                ctx.session_id,
            )
            return AgentResult(response=response_text, session_id=ctx.session_id, files=[file_override])

        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning(
                "Recruiter agent returned non-JSON output; applying fallback | session=%s",
                ctx.session_id,
            )
            translated_text, translated_flag = recruiter_service.translate_description(description)
            matches = recruiter_service.search_candidates(translated_text)
            payload = {
                "query": translated_text,
                "translated": translated_flag,
                "matches": [match.as_dict() for match in matches],
                "fallback": True,
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
        logger.info(
            "Recruiter match workflow responded | session=%s | matches=%d",
            ctx.session_id,
            len(files),
        )
        return AgentResult(response=payload, session_id=ctx.session_id, files=files)
