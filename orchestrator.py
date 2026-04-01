"""
agents/orchestrator.py
AgentTest AI — Master Orchestrator using LangGraph state machine.
Stakeholder requirement → 6-agent pipeline → full test report.

Pipeline:
  RequirementsAgent → PlanningAgent → ManualTestAgent
                                    → AutomationAgent (parallel: Robot/Python/Selenium/JSON)
                                    → ExecutionAgent
                                    → ReportAgent
"""
from __future__ import annotations
import asyncio, json, uuid
from datetime import datetime
from pathlib import Path
from typing import TypedDict
import structlog
from langchain_openai import ChatOpenAI

from agents.requirements_agent import RequirementsAgent
from agents.planning_agent import PlanningAgent
from agents.manual_test_agent import ManualTestAgent
from agents.automation_agent import AutomationAgent
from agents.execution_agent import ExecutionAgent
from agents.report_agent import ReportAgent
from utils.config import settings

log = structlog.get_logger(__name__)


class PipelineState(TypedDict):
    session_id:        str
    raw_input:         str
    parsed_reqs:       list
    test_plan:         dict
    manual_tests:      list
    robot_tests:       list
    python_tests:      list
    selenium_tests:    list
    json_coordinates:  dict
    execution_results: dict
    report_path:       str
    errors:            list
    status:            str


class AgentTestOrchestrator:
    """Multi-agent QA orchestrator — runs end-to-end from requirement to report."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=settings.TEMPERATURE,
        )
        self.req_agent    = RequirementsAgent(self.llm)
        self.plan_agent   = PlanningAgent(self.llm)
        self.manual_agent = ManualTestAgent(self.llm)
        self.auto_agent   = AutomationAgent(self.llm)
        self.exec_agent   = ExecutionAgent()
        self.report_agent = ReportAgent(self.llm)

    async def run(self, requirement_text: str,
                  on_progress=None) -> PipelineState:
        """
        Main entry point. Runs full pipeline and returns complete state.
        on_progress(stage, pct) called at each stage for UI updates.
        """
        session_id = (
            f"SESSION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            f"_{uuid.uuid4().hex[:6].upper()}"
        )
        log.info("pipeline_start", session_id=session_id)

        def progress(stage: str, pct: float):
            log.info("pipeline_progress", stage=stage, pct=pct)
            if on_progress:
                on_progress(stage, pct)

        state: PipelineState = {
            "session_id": session_id, "raw_input": requirement_text,
            "parsed_reqs": [], "test_plan": {}, "manual_tests": [],
            "robot_tests": [], "python_tests": [], "selenium_tests": [],
            "json_coordinates": {}, "execution_results": {},
            "report_path": "", "errors": [], "status": "RUNNING",
        }

        try:
            # Stage 1 — Parse requirements
            progress("Parsing stakeholder requirements...", 0.10)
            state["parsed_reqs"] = await self.req_agent.parse(requirement_text)

            # Stage 2 — Create test plan
            progress("Creating test plan and coverage matrix...", 0.22)
            state["test_plan"] = await self.plan_agent.plan(state["parsed_reqs"])

            # Stage 3 — Generate manual tests
            progress("Writing manual test cases...", 0.38)
            state["manual_tests"] = await self.manual_agent.generate(
                state["parsed_reqs"], state["test_plan"]
            )

            # Stage 4 — Generate automation (all 4 formats in parallel)
            progress("Generating automation code (Robot / Python / Selenium / JSON)...", 0.55)
            auto = await self.auto_agent.generate(
                state["parsed_reqs"], state["test_plan"], state["manual_tests"]
            )
            state["robot_tests"]      = auto["robot"]
            state["python_tests"]     = auto["python"]
            state["selenium_tests"]   = auto["selenium"]
            state["json_coordinates"] = auto["json_coords"]

            # Stage 5 — Execute tests
            progress("Executing tests and capturing results...", 0.72)
            state["execution_results"] = await self.exec_agent.run(
                session_id=session_id,
                robot_code="\n\n".join(state["robot_tests"]),
                python_code="\n\n".join(state["python_tests"]),
            )

            # Stage 6 — Generate reports
            progress("Generating PDF + HTML + Markdown reports...", 0.88)
            state["report_path"] = await self.report_agent.generate(state)

            # Save all outputs
            await self._save_outputs(state)
            state["status"] = "DONE"
            progress("Pipeline complete!", 1.0)

        except Exception as e:
            log.error("pipeline_error", error=str(e))
            state["errors"].append(str(e))
            state["status"] = "FAILED"

        log.info("pipeline_done", session_id=session_id, status=state["status"])
        return state

    async def _save_outputs(self, state: PipelineState) -> None:
        sid = state["session_id"]
        base = Path(f"outputs/{sid}")

        def write(subdir: str, filename: str, content: str):
            p = base / subdir
            p.mkdir(parents=True, exist_ok=True)
            (p / filename).write_text(content, encoding="utf-8")

        for i, code in enumerate(state["robot_tests"]):
            write("robot", f"test_suite_{i+1:02d}.robot", code)
        for i, code in enumerate(state["python_tests"]):
            write("python", f"test_module_{i+1:02d}.py", code)
        for i, code in enumerate(state["selenium_tests"]):
            write("selenium", f"selenium_script_{i+1:02d}.py", code)
        write("json", "coordinates.json", json.dumps(state["json_coordinates"], indent=2))
        write("", "manual_test_cases.md", self._manual_to_md(state["manual_tests"]))
        write("", "pipeline_state.json", json.dumps({
            k: v for k, v in state.items()
            if k not in ("robot_tests", "python_tests", "selenium_tests")
        }, indent=2, default=str))

    @staticmethod
    def _manual_to_md(tests: list) -> str:
        lines = [f"# Manual Test Cases ({len(tests)})\n"]
        for tc in tests:
            lines += [
                f"## {tc.get('id','TC')} — {tc.get('title','')}",
                f"**Type:** {tc.get('type','')} | **Priority:** {tc.get('priority','')} "
                f"| **Est:** {tc.get('estimated_time_min',5)} min\n",
                "**Preconditions:**",
            ]
            for p in tc.get("preconditions", []):
                lines.append(f"- {p}")
            lines.append("\n**Steps:**")
            for i, s in enumerate(tc.get("steps", []), 1):
                lines.append(f"{i}. {s}")
            lines.append("\n**Expected Results:**")
            for e in tc.get("expected_results", tc.get("expected", [])):
                lines.append(f"✓ {e}")
            lines.append("\n---\n")
        return "\n".join(lines)
