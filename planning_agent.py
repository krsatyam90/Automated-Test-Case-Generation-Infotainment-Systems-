"""
agents/planning_agent.py
Creates a comprehensive test plan: levels, priorities, coverage matrix,
effort estimates, risk areas, entry/exit criteria.
"""
from __future__ import annotations
import json, re
import structlog
from langchain_core.messages import SystemMessage, HumanMessage

log = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are a QA test planning expert for automotive IVI systems.
Given structured requirements, create a comprehensive test plan.

Return a JSON object:
{
  "test_plan_id": "TP-XXXXXXXX",
  "summary": "one-line summary",
  "scope": ["in-scope areas"],
  "out_of_scope": ["exclusions"],
  "test_levels": {
    "unit":        {"enabled": true, "priority": "High"},
    "integration": {"enabled": true, "priority": "High"},
    "system":      {"enabled": true, "priority": "Critical"},
    "regression":  {"enabled": true, "priority": "Medium"}
  },
  "coverage_matrix": [
    {
      "req_id": "REQ-XXX", "title": "...", "priority": "High",
      "manual": true, "automation": true,
      "robot": true, "selenium": true, "python": true,
      "estimated_tc": 3, "estimated_hours": 2
    }
  ],
  "risk_areas": ["high-risk areas"],
  "entry_criteria": ["conditions before testing starts"],
  "exit_criteria": ["conditions for test completion"],
  "estimated_effort": {"manual_hours": N, "automation_hours": N},
  "execution_order": ["REQ-ID in order"]
}
Return ONLY valid JSON."""


class PlanningAgent:
    def __init__(self, llm):
        self.llm = llm

    async def plan(self, parsed_reqs: list[dict]) -> dict:
        log.info("plan_agent_start", reqs=len(parsed_reqs))
        response = await self.llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Create test plan:\n{json.dumps(parsed_reqs, indent=2)}"),
        ])
        plan = self._safe_parse(response.content)
        log.info("plan_agent_done", plan_id=plan.get("test_plan_id", "?"))
        return plan

    @staticmethod
    def _safe_parse(raw: str) -> dict:
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        try:
            return json.loads(raw)
        except Exception:
            return {"test_plan_id": "TP-ERROR", "coverage_matrix": [], "risk_areas": []}
