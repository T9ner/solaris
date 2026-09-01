"""Canonical trajectory logger for Forge autonomous agent runs.

Writes dual-format execution records:
1. Structured JSON (.json) for machine evaluation and automated benchmark scoring.
2. Formatted Markdown (.md) for human audits, PR reviews, and post-mortems.
"""

import json
import os
import pathlib
import time
from typing import Optional
from agents.state import PipelineState, TrajectoryEvent


class TrajectoryLogger:
    """Manages append-only recording and file export of pipeline runs."""

    @staticmethod
    def record_step(state: PipelineState, node_name: str, description: str, data: Optional[dict] = None) -> None:
        event = TrajectoryEvent(
            node=node_name,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            description=description,
            data_snapshot=data or {},
        )
        state.trajectories.append(event)

    @staticmethod
    def save_trajectory(state: PipelineState, base_path: str) -> None:
        path = pathlib.Path(base_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        json_path = path.with_suffix(".json")
        md_path = path.with_suffix(".md")

        # 1. Save structured JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(), f, indent=2)

        # 2. Save human-readable Markdown
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Forge Autonomous Execution Trajectory: {state.case_id}\n\n")
            f.write(f"- **Task**: {state.task_description}\n")
            f.write(f"- **Environment**: {state.environment_mode}\n")
            f.write(f"- **Status**: {'APPROVED' if state.approved else ('REJECTED' if state.approved is False else 'PENDING')}\n")
            f.write(f"- **Discrepancies Found**: {len(state.discrepancies)}\n")
            f.write(f"- **Actions Executed**: {len(state.executed_actions)}\n")
            f.write(f"- **Execution Time**: {state.execution_time_seconds:.2f}s\n")
            f.write(f"- **Total Token Usage**: {state.token_usage:,}\n\n")

            f.write("## Discrepancies Surfaced\n\n")
            if not state.discrepancies:
                f.write("No cross-system discrepancies found.\n\n")
            else:
                for gap in state.discrepancies:
                    f.write(f"### [{gap.severity.upper()}] {gap.title} (`{gap.gap_id}`)\n")
                    f.write(f"- **Category**: `{gap.category}`\n")
                    f.write(f"- **Affected Systems**: {', '.join(gap.affected_tools)}\n")
                    f.write(f"- **Details**: {gap.description}\n")
                    f.write(f"- **Recommended Action**: {gap.recommended_action}\n\n")

            f.write("## Resolution & Execution Steps\n\n")
            if not state.executed_actions:
                f.write("No execution actions required.\n\n")
            else:
                for action in state.executed_actions:
                    f.write(f"### Action `{action.action_id}` on `{action.target_tool}`\n")
                    f.write(f"- **Type**: `{action.action_type}`\n")
                    f.write(f"- **Success**: `{action.success}`\n")
                    if action.file_path:
                        f.write(f"- **File**: `{action.file_path}`\n")
                    if action.preview_url:
                        f.write(f"- **Live Preview**: [{action.preview_url}]({action.preview_url})\n")
                    if action.output_preview:
                        f.write("```\n" + action.output_preview.strip() + "\n```\n")
                    f.write("\n")

            if state.verification:
                f.write("## Verification Summary\n\n")
                f.write(f"- **Verified**: `{state.verification.verified}`\n")
                f.write(f"- **Test Suite Passed**: `{state.verification.test_suite_passed}`\n")
                f.write(f"- **Preview Reachable**: `{state.verification.preview_reachable}`\n")
                if state.verification.preview_url:
                    f.write(f"- **Preview URL**: {state.verification.preview_url}\n")
                f.write(f"- **rrweb Events Logged**: {state.verification.rrweb_replay_events}\n\n")

            if state.executive_brief:
                f.write("## Executive Brief\n\n")
                f.write(state.executive_brief + "\n\n")

            f.write("## Step-by-Step Node Log\n\n")
            for event in state.trajectories:
                f.write(f"- **[{event.timestamp}] Node `{event.node}`**: {event.description}\n")
