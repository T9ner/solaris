"""Typed state models for the Forge Autonomous Operations Pipeline.

Defines schemas for all state transitions, tool signals, and discrepancy findings.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolSignal(BaseModel):
    """Normalized structured signal extracted from a connected tool."""
    tool_name: str
    signal_type: str  # e.g., 'pull_request', 'issue', 'ticket', 'web_page', 'payment_event', 'sentry_error'
    entity_id: str
    title: str
    status: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    raw_snippet: Optional[str] = None


class DiscrepancyReport(BaseModel):
    """Cross-system discrepancy or drift identified between tools."""
    gap_id: str
    category: str  # 'status_drift', 'untracked_bug', 'release_regression', 'payment_mismatch', 'doc_outdated'
    severity: str  # 'critical', 'high', 'medium', 'low'
    title: str
    description: str
    affected_tools: List[str]
    evidence: Dict[str, Any] = Field(default_factory=dict)
    recommended_action: str


class ResolutionAction(BaseModel):
    """An action executed in Sandbox or Desktop to resolve a discrepancy."""
    action_id: str
    gap_id: str
    target_tool: str
    action_type: str  # 'sandbox_patch', 'sandbox_test', 'port_preview', 'desktop_gui_update', 'status_sync'
    command_or_code: Optional[str] = None
    file_path: Optional[str] = None
    output_preview: Optional[str] = None
    preview_url: Optional[str] = None
    success: bool = False


class VerificationResult(BaseModel):
    """Result of automated verification against preview URL and test suites."""
    verified: bool
    test_suite_passed: bool
    preview_reachable: bool
    preview_url: Optional[str] = None
    rrweb_replay_events: int = 0
    verification_log: str = ""


class TrajectoryEvent(BaseModel):
    """A single step in the canonical execution trajectory."""
    node: str
    timestamp: str
    description: str
    data_snapshot: Dict[str, Any] = Field(default_factory=dict)


class PipelineState(BaseModel):
    """Complete typed state flowing through every node of the LangGraph state machine."""
    case_id: str
    task_description: str
    environment_mode: str = "mock"  # 'mock' or 'live'

    # Sense Node outputs
    signals: List[ToolSignal] = Field(default_factory=list)
    web_extractions: List[Dict[str, Any]] = Field(default_factory=list)

    # Decide Node outputs
    discrepancies: List[DiscrepancyReport] = Field(default_factory=list)
    resolution_plan: List[str] = Field(default_factory=list)

    # Execute Node outputs
    sandbox_id: Optional[str] = None
    desktop_id: Optional[str] = None
    executed_actions: List[ResolutionAction] = Field(default_factory=list)

    # Verify Node outputs
    verification: Optional[VerificationResult] = None

    # Approval Node outputs
    approval_required: bool = True
    approved: Optional[bool] = None
    reviewer_comments: Optional[str] = None

    # Final Output and Telemetry
    executive_brief: Optional[str] = None
    execution_time_seconds: float = 0.0
    token_usage: int = 0
    trajectories: List[TrajectoryEvent] = Field(default_factory=list)
