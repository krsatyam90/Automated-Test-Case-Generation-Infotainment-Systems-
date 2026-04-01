"""
agents/manual_test_agent.py
Generates detailed manual test cases a human QA tester can follow.
Produces positive, negative, and edge cases for every requirement.
"""
from __future__ import annotations
import json, re
import structlog
from langchain_core.messages import SystemMessage, HumanMessage

log = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are a senior manual QA engineer for automotive infotainment systems (IVI).

Generate comprehensive manual test cases. For EACH requirement produce AT MINIMUM:
- 1 positive (happy path) test case
- 1 negative (failure/invalid input) test case
- 1 edge/boundary case

Each test case JSON object:
{
  "id": "TC_XXXXXX_POS",
  "req_id": "REQ-XXXXXX",
  "title": "clear, specific title",
  "type": "positive|negative|edge",
  "priority": "Critical|High|Medium|Low",
  "test_level": "unit|integration|system",
  "environment": "HiL Bench|Simulation|Real Vehicle",
  "preconditions": ["setup steps"],
  "test_data": {"key": "value"},
  "steps": ["numbered step a human follows"],
  "expected_results": ["observable outcome to verify"],
  "actual_result": "",
  "status": "NOT_RUN",
  "defect_ids": [],
  "estimated_time_min": 5,
  "notes": "constraints or special instructions"
}

Return ONLY a JSON array of test case objects. No markdown."""


class ManualTestAgent:
    def __init__(self, llm):
        self.llm = llm

    async def generate(self, parsed_reqs: list[dict], test_plan: dict) -> list[dict]:
        log.info("manual_agent_start", reqs=len(parsed_reqs))
        coverage = test_plan.get("coverage_matrix", [])
        response = await self.llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=(
                f"Requirements:\n{json.dumps(parsed_reqs, indent=2)}\n\n"
                f"Coverage matrix:\n{json.dumps(coverage, indent=2)}\n\n"
                "Generate complete manual test cases for all requirements."
            )),
        ])
        tests = self._safe_parse(response.content)
        log.info("manual_agent_done", count=len(tests))
        return tests

    @staticmethod
    def _safe_parse(raw: str) -> list[dict]:
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        try:
            data = json.loads(raw)
        except Exception:
            return []
        if isinstance(data, list):
            return data
        for key in ("test_cases", "tests", "cases"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return []
