"""Unit tests for PipelineState and data models."""

import pytest
from agents.state import (
    ToolSignal,
    DiscrepancyReport,
    ResolutionAction,
    VerificationResult,
    PipelineState,
)


def test_tool_signal_instantiation():
    signal = ToolSignal(
        tool_name="github",
        signal_type="pull_request",
        entity_id="101",
        title="feat: add oauth",
        status="merged",
    )
    assert signal.tool_name == "github"
    assert signal.status == "merged"
    assert signal.payload == {}


def test_discrepancy_report_instantiation():
    gap = DiscrepancyReport(
        gap_id="gap_1",
        category="status_drift",
        severity="high",
        title="Status drift",
        description="PR merged, ticket open",
        affected_tools=["github", "linear"],
        recommended_action="Close ticket",
    )
    assert gap.severity == "high"
    assert "linear" in gap.affected_tools


def test_pipeline_state_lifecycle():
    state = PipelineState(
        case_id="test_case_01",
        task_description="Verify release pipeline",
    )
    assert state.case_id == "test_case_01"
    assert state.environment_mode == "mock"
    assert state.discrepancies == []
    assert state.approved is None
