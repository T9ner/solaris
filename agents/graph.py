"""LangGraph state machine for Forge Autonomous Operations Pipeline.

Orchestrates:
Sense -> Decide -> Execute -> Verify -> Approve (Human-in-the-loop checkpoint) -> Save
"""

import argparse
import asyncio
import json
import os
import pathlib
import sys
import time
from typing import Any, Dict, Optional

# Ensure project root is on sys.path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agents.state import PipelineState
from agents.sensing import SensingNode
from agents.reasoning import ReasoningNode
from agents.execution import ExecutionNode
from agents.verification import VerificationNode
from agents.trace import TrajectoryLogger
from infrastructure import create_infrastructure_drivers
from services.report import ExecutiveReportService


class ForgePipeline:
    """State machine coordinator for the autonomous worker pipeline."""

    def __init__(
        self,
        use_mock: bool = True,
        api_key: Optional[str] = None,
        auto_approve: bool = False,
    ):
        self.use_mock = use_mock
        self.auto_approve = auto_approve

        browser_driver, sandbox_driver, desktop_driver = create_infrastructure_drivers(
            use_mock=use_mock,
            api_key=api_key,
        )

        self.sensing_node = SensingNode(browser_driver)
        self.reasoning_node = ReasoningNode()
        self.execution_node = ExecutionNode(sandbox_driver, desktop_driver)
        self.verification_node = VerificationNode(browser_driver)
        self.report_service = ExecutiveReportService()

    async def run(
        self,
        case_data: Dict[str, Any],
        case_id: Optional[str] = None,
        task_desc: Optional[str] = None,
        trace_path: Optional[str] = None,
    ) -> PipelineState:
        start_time = time.time()

        case_id = case_id or case_data.get("case_id", "audit_run")
        task_desc = task_desc or case_data.get("description", "Autonomous Cross-System Integrity Audit")

        state = PipelineState(
            case_id=case_id,
            task_description=task_desc,
            environment_mode="mock" if self.use_mock else "live",
        )

        TrajectoryLogger.record_step(state, "START", f"Starting Forge Autonomous Pipeline for {case_id}")

        # 1. SENSE NODE
        state = await self.sensing_node.execute(state, raw_case_data=case_data)

        # 2. DECIDE NODE
        state = await self.reasoning_node.execute(state)

        # 3. EXECUTE NODE (Conditional on discrepancies existing)
        if state.discrepancies:
            state = await self.execution_node.execute(state)
            # 4. VERIFY NODE
            state = await self.verification_node.execute(state)

        # 5. GENERATE EXECUTIVE BRIEF
        brief = self.report_service.generate_brief(
            case_id=state.case_id,
            task_description=state.task_description,
            discrepancies=state.discrepancies,
            actions=state.executed_actions,
            verification=state.verification,
        )
        state.executive_brief = brief

        # 6. APPROVE NODE (Human-in-the-loop checkpoint)
        if state.discrepancies:
            if self.auto_approve:
                state.approved = True
                TrajectoryLogger.record_step(state, "APPROVE", "Checkpoint auto-approved via CLI flag")
            else:
                # Terminal checkpoint interaction
                print("\n" + "=" * 60)
                print("HUMAN APPROVAL CHECKPOINT (Forge Interrupt)")
                print("=" * 60)
                print(f"Case ID: {state.case_id}")
                print(f"Discrepancies Found: {len(state.discrepancies)}")
                for gap in state.discrepancies:
                    print(f" - [{gap.severity.upper()}] {gap.title}")
                print("\nExecute and publish this resolution plan? [y/N]: ", end="", flush=True)

                if sys.stdin.isatty():
                    user_input = sys.stdin.readline().strip().lower()
                    if user_input in ("y", "yes"):
                        state.approved = True
                        TrajectoryLogger.record_step(state, "APPROVE", "Checkpoint approved by human operator")
                    else:
                        state.approved = False
                        TrajectoryLogger.record_step(state, "APPROVE", "Checkpoint rejected by human operator")
                else:
                    state.approved = True
                    TrajectoryLogger.record_step(state, "APPROVE", "Non-interactive environment, proceeding with approval")
        else:
            state.approved = True
            TrajectoryLogger.record_step(state, "APPROVE", "Zero gaps detected, approval not required")

        state.execution_time_seconds = round(time.time() - start_time, 2)
        TrajectoryLogger.record_step(
            state,
            "SAVE",
            f"Pipeline run completed in {state.execution_time_seconds}s with {len(state.discrepancies)} gaps",
        )

        # Save trajectory files if requested
        if trace_path:
            TrajectoryLogger.save_trajectory(state, trace_path)

        return state


def main():
    parser = argparse.ArgumentParser(description="Forge Autonomous Pipeline CLI Runner")
    parser.add_argument("--case", type=str, required=True, help="Path to input test case JSON file")
    parser.add_argument("--mock", action="store_true", default=True, help="Use mock drivers for offline simulation")
    parser.add_argument("--live", action="store_true", help="Use live Solari API and LLM endpoints")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve checkpoint without prompting")
    parser.add_argument("--trace", type=str, default=None, help="Base path to save trajectory logs (.json and .md)")

    args = parser.parse_args()

    case_path = pathlib.Path(args.case)
    if not case_path.exists():
        print(f"Error: Test case file '{args.case}' not found.")
        sys.exit(1)

    with open(case_path, "r", encoding="utf-8") as f:
        case_data = json.load(f)

    use_mock = not args.live
    pipeline = ForgePipeline(use_mock=use_mock, auto_approve=args.auto_approve)

    state = asyncio.run(pipeline.run(
        case_data=case_data,
        case_id=case_data.get("case_id", case_path.stem),
        task_desc=case_data.get("description", "Cross-system Stack Audit"),
        trace_path=args.trace,
    ))

    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    print(f"Case: {state.case_id}")
    print(f"Status: {'APPROVED' if state.approved else 'REJECTED'}")
    print(f"Discrepancies: {len(state.discrepancies)}")
    print(f"Execution Time: {state.execution_time_seconds}s")
    print(f"Token Count: {state.token_usage:,}")
    if state.verification and state.verification.preview_url:
        print(f"Live Preview: {state.verification.preview_url}")
    print("=" * 60)


if __name__ == "__main__":
    main()
