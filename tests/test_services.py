"""Unit tests for domain services (Audit, Patcher, Report)."""

import asyncio
from agents.state import ToolSignal, DiscrepancyReport
from services.audit import CrossSystemAuditService
from services.patcher import SandboxPatcherService
from services.report import ExecutiveReportService
from infrastructure.mock_driver import MockSandboxDriver


def test_cross_system_audit_pr_status_drift():
    signals = [
        ToolSignal(
            tool_name="github",
            signal_type="pull_request",
            entity_id="101",
            title="feat: add oauth [ENG-402]",
            status="merged",
            payload={"linear_issue_id": "ENG-402"},
        ),
        ToolSignal(
            tool_name="linear",
            signal_type="ticket",
            entity_id="ENG-402",
            title="Add OAuth",
            status="in_progress",
        ),
    ]

    service = CrossSystemAuditService()
    gaps = service.audit_signals(signals)

    assert len(gaps) == 1
    assert gaps[0].category == "status_drift"
    assert gaps[0].severity == "high"
    assert "ENG-402" in gaps[0].description


def test_cross_system_audit_stripe_pricing_mismatch():
    signals = [
        ToolSignal(
            tool_name="web_portal",
            signal_type="web_page",
            entity_id="https://company.com/pricing",
            title="Pricing Page",
            status="reachable",
            payload={"plans": {"Pro": 49}},
        ),
        ToolSignal(
            tool_name="stripe",
            signal_type="payment_event",
            entity_id="evt_1",
            title="Stripe Plans",
            status="active",
            payload={"plans": {"Pro": 59}},
        ),
    ]

    service = CrossSystemAuditService()
    gaps = service.audit_signals(signals)

    assert len(gaps) == 1
    assert gaps[0].category == "payment_mismatch"
    assert "Web ($49) vs Stripe ($59)" in gaps[0].title


def test_sandbox_patcher_service():
    async def run():
        sandbox_driver = MockSandboxDriver()
        sbx_id = await sandbox_driver.create_sandbox()
        patcher = SandboxPatcherService(sandbox_driver)

        await patcher.setup_workspace(sbx_id, {"/tmp/main.py": "def test(): pass"})
        await patcher.apply_patch(sbx_id, "/tmp/main.py", "def test(): return True")

        test_res = await patcher.run_test_suite(sbx_id)
        assert test_res.exit_code == 0

        preview_res = await patcher.launch_preview_server(sbx_id, port=3000)
        assert preview_res.port == 3000
        assert "preview.getsolari.com" in preview_res.url

    asyncio.run(run())


def test_executive_report_generation():
    gaps = [
        DiscrepancyReport(
            gap_id="gap_1",
            category="status_drift",
            severity="high",
            title="PR merged with open ticket",
            description="Details here",
            affected_tools=["github", "linear"],
            recommended_action="Close ticket",
        )
    ]
    report = ExecutiveReportService.generate_brief(
        case_id="case_01",
        task_description="Test task",
        discrepancies=gaps,
        actions=[],
    )
    assert "Forge Executive Stack Audit: case_01" in report
    assert "PR merged with open ticket" in report
