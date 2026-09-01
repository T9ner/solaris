"""Domain service for generating executive intelligence briefs and discrepancy scorecards."""

import time
from typing import List, Optional
from agents.state import DiscrepancyReport, ResolutionAction, VerificationResult


class ExecutiveReportService:
    """Generates structured markdown briefs and audit summaries."""

    @staticmethod
    def generate_brief(
        case_id: str,
        task_description: str,
        discrepancies: List[DiscrepancyReport],
        actions: List[ResolutionAction],
        verification: Optional[VerificationResult] = None,
    ) -> str:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        lines = []

        lines.append(f"# Forge Executive Stack Audit: {case_id}")
        lines.append(f"**Generated**: {timestamp} | **Scope**: Cross-System Integrity Audit\n")
        lines.append(f"**Task Objective**: {task_description}\n")

        # 1. Executive Summary Table
        critical_count = sum(1 for d in discrepancies if d.severity == "critical")
        high_count = sum(1 for d in discrepancies if d.severity == "high")
        resolved_count = sum(1 for a in actions if a.success)

        lines.append("## Executive Summary")
        lines.append(f"- **Total Discrepancies Surfaced**: {len(discrepancies)}")
        lines.append(f"- **Critical Gaps**: {critical_count} | **High Severity**: {high_count}")
        lines.append(f"- **Autonomous Actions Executed**: {len(actions)} ({resolved_count} succeeded)")
        if verification:
            lines.append(f"- **Verification Status**: {'VERIFIED' if verification.verified else 'FAILED'}")
            if verification.preview_url:
                lines.append(f"- **Live Staging Preview**: [{verification.preview_url}]({verification.preview_url})")
        lines.append("")

        # 2. Identified Discrepancies
        lines.append("## Discrepancy Details")
        if not discrepancies:
            lines.append("No cross-system discrepancies detected. All monitored tools are in sync.\n")
        else:
            for i, gap in enumerate(discrepancies, 1):
                lines.append(f"### {i}. [{gap.severity.upper()}] {gap.title}")
                lines.append(f"- **Category**: `{gap.category}`")
                lines.append(f"- **Affected Tools**: {', '.join(gap.affected_tools)}")
                lines.append(f"- **Description**: {gap.description}")
                lines.append(f"- **Recommended Resolution**: {gap.recommended_action}\n")

        # 3. Action & Patch Log
        lines.append("## Autonomous Execution Log")
        if not actions:
            lines.append("No runtime actions were required.\n")
        else:
            for action in actions:
                lines.append(f"- **[{action.target_tool.upper()}] {action.action_type}** (`{action.action_id}`)")
                if action.file_path:
                    lines.append(f"  - File: `{action.file_path}`")
                if action.preview_url:
                    lines.append(f"  - Preview: [{action.preview_url}]({action.preview_url})")
                if action.output_preview:
                    lines.append(f"  - Output: `{action.output_preview.strip()}`")
                lines.append(f"  - Result: `{'SUCCESS' if action.success else 'FAILED'}`")
            lines.append("")

        # 4. Next Steps
        lines.append("## Human Review Checkpoint")
        lines.append("Review the surfaced discrepancies and verified patches above before confirming final synchronization across live production APIs.")

        return "\n".join(lines)
