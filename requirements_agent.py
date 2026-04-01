"""
agents/requirements_agent.py
Parses raw stakeholder requirements (text / docx / pdf / excel)
into structured, test-ready specifications using GPT-4o.
"""
from __future__ import annotations
import json, re
import structlog
from langchain_core.messages import SystemMessage, HumanMessage

log = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are a senior QA requirements analyst specialising in automotive
infotainment systems (IVI). Parse stakeholder requirements and extract structured
test-ready specifications.

For each requirement produce a JSON object:
{
  "id": "REQ-XXXXXX",
  "title": "short descriptive title",
  "description": "full requirement text",
  "domain": "Bluetooth|Media|Navigation|VoiceControl|USB|Phone|ADAS|Generic",
  "priority": "Critical|High|Medium|Low",
  "acceptance_criteria": ["measurable pass/fail criteria"],
  "timing_constraints": {"value": N, "unit": "ms|s", "description": "..."},
  "negative_scenarios": ["failure modes to test"],
  "tags": ["relevant tags"]
}

Return ONLY a JSON array. No markdown, no explanation."""


class RequirementsAgent:
    def __init__(self, llm):
        self.llm = llm

    async def parse(self, raw_text: str) -> list[dict]:
        log.info("req_agent_start", chars=len(raw_text))
        response = await self.llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Parse these stakeholder requirements:\n\n{raw_text}"),
        ])
        parsed = self._safe_parse(response.content)
        log.info("req_agent_done", count=len(parsed))
        return parsed

    @staticmethod
    def _safe_parse(raw: str) -> list[dict]:
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        try:
            data = json.loads(raw)
        except Exception:
            return []
        if isinstance(data, list):
            return data
        for key in ("requirements", "reqs", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return []
