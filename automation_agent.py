"""
agents/automation_agent.py
Generates all 4 automation artifacts in parallel:
  Robot Framework · Python pytest · Selenium WebDriver · JSON UI coordinates
"""
from __future__ import annotations
import asyncio, json, re
import structlog
from langchain_core.messages import SystemMessage, HumanMessage

log = structlog.get_logger(__name__)

ROBOT_SYS = """You are an expert Robot Framework QA engineer for automotive IVI systems.
Convert manual test cases to a complete Robot Framework test suite.

Rules:
- Import TAF_PATH resources matching real IVI project structure
- Use proper Suite Setup/Teardown, Test Setup/Teardown
- Add [Documentation], [Tags], [Setup] to every test case
- Use meaningful variables in *** Variables *** section
- Add Keywords section with reusable keywords
- Include timing assertions for SLA requirements
- Return ONLY the complete .robot file. No markdown."""

PYTHON_SYS = """You are an expert pytest engineer for automotive IVI systems.
Convert manual test cases to a complete pytest module.

Rules:
- Use dataclasses for test data models
- Use fixtures with correct scope (function/module/session)
- Add parametrised tests where applicable
- Use time.perf_counter() for timing assertions
- Mock hardware with MagicMock
- Full type hints on all functions
- Return ONLY the complete .py file. No markdown."""

SELENIUM_SYS = """You are an expert Selenium 4 WebDriver engineer for IVI HMI automation.
Convert manual test cases to Selenium scripts using Page Object Model.

Rules:
- Always use WebDriverWait + expected_conditions (NEVER time.sleep)
- Headless Chrome options for CI/CD
- Screenshot on failure via pytest hooks
- Meaningful locator strategies (ID > CSS > XPATH)
- Return ONLY the complete .py file. No markdown."""

JSON_SYS = """You are a UI automation expert for automotive IVI HMI (1280x720 pixels).
Generate a JSON action map from the manual test cases.

Return JSON:
{
  "metadata": {"resolution": "1280x720", "touch_unit": "pixels"},
  "ui_elements": {
    "element_name": {"x": N, "y": N, "width": N, "height": N, "action": "TAP|TYPE|SWIPE|WAIT"}
  },
  "test_sequences": {
    "TC_ID": {
      "steps": [
        {"step": N, "action": "TAP", "element": "name",
         "coordinates": {"x": N, "y": N},
         "expected_state": "STATE_NAME",
         "screenshot": "TC_ID_stepN.png"}
      ],
      "assertions": [{"field": "x", "operator": "EQUALS|BETWEEN|REGEX", "expected": "y"}]
    }
  },
  "screenshot_convention": "FAIL_{TC_ID}_{STEP}_{TIMESTAMP}.png",
  "log_convention": "{TC_ID}_{DATE}.log"
}
Return ONLY valid JSON."""


class AutomationAgent:
    def __init__(self, llm):
        self.llm = llm

    async def generate(self, parsed_reqs: list[dict],
                       test_plan: dict,
                       manual_tests: list[dict]) -> dict:
        log.info("auto_agent_start", manual_tests=len(manual_tests))
        # Cap to avoid token overflow
        tc_text = json.dumps(manual_tests[:12], indent=2)

        robot, python, selenium, json_coords = await asyncio.gather(
            self._call(ROBOT_SYS,   f"Generate Robot Framework suite:\n{tc_text}"),
            self._call(PYTHON_SYS,  f"Generate pytest module:\n{tc_text}"),
            self._call(SELENIUM_SYS, f"Generate Selenium script:\n{tc_text}"),
            self._call_json(JSON_SYS, f"Generate coordinates map:\n{tc_text}"),
        )
        log.info("auto_agent_done")
        return {
            "robot":      [robot],
            "python":     [python],
            "selenium":   [selenium],
            "json_coords": json_coords,
        }

    async def _call(self, system: str, user: str) -> str:
        r = await self.llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=user),
        ])
        return r.content.strip()

    async def _call_json(self, system: str, user: str) -> dict:
        r = await self.llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content=user),
        ])
        raw = re.sub(r"```(?:json)?|```", "", r.content).strip()
        try:
            return json.loads(raw)
        except Exception:
            return {"error": "parse_failed", "raw": raw[:200]}
