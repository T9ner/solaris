"""Integration tests for ForgePipeline state machine."""

import asyncio
from agents.graph import ForgePipeline


def test_forge_pipeline_full_execution_case_01():
    async def run():
        case_data = {
            "case_id": "test_case_01",
            "description": "Weekly status sync audit",
            "github_prs": [
                {
                    "id": "101",
                    "title": "feat: auth [ENG-402]",
                    "status": "merged",
                    "linear_issue_id": "ENG-402",
                }
            ],
            "linear_tickets": [
                {
                    "id": "ENG-402",
                    "title": "Auth feature",
                    "status": "in_progress",
                }
            ],
        }

        pipeline = ForgePipeline(use_mock=True, auto_approve=True)
        state = await pipeline.run(case_data=case_data)

        assert state.case_id == "test_case_01"
        assert len(state.discrepancies) == 1
        assert state.discrepancies[0].category == "status_drift"
        assert len(state.executed_actions) > 0
        assert state.approved is True
        assert state.verification is not None
        assert state.verification.verified is True
        assert state.executive_brief is not None
        assert len(state.trajectories) >= 5

    asyncio.run(run())


def test_forge_pipeline_clean_case_zero_gaps():
    async def run():
        case_data = {
            "case_id": "test_clean_case",
            "description": "Clean audit",
            "github_prs": [
                {
                    "id": "101",
                    "title": "docs: update [DOCS-1]",
                    "status": "merged",
                    "linear_issue_id": "DOCS-1",
                }
            ],
            "linear_tickets": [
                {
                    "id": "DOCS-1",
                    "title": "Update docs",
                    "status": "done",
                }
            ],
        }

        pipeline = ForgePipeline(use_mock=True, auto_approve=True)
        state = await pipeline.run(case_data=case_data)

        assert len(state.discrepancies) == 0
        assert len(state.executed_actions) == 0
        assert state.approved is True

    asyncio.run(run())
