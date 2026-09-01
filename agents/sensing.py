"""Sense Node for Forge Autonomous Operations.

Collects structured signals from connected APIs and web portals:
- GitHub: Pull Requests, Issues, Commits
- Linear: Issues, Sprints, Statuses
- Sentry: Production Error Events and Stacktraces
- Stripe: Billing Plans and Subscriptions
- Web Portal: Live marketing and documentation pages extracted via Solari Browser
"""

import json
from typing import Any, Dict, List, Optional
from agents.state import PipelineState, ToolSignal
from agents.trace import TrajectoryLogger
from infrastructure.base import BaseBrowserDriver


class SensingNode:
    """Orchestrates multi-source signal extraction across APIs and Browsers."""

    def __init__(self, browser_driver: BaseBrowserDriver):
        self.browser_driver = browser_driver

    async def execute(self, state: PipelineState, raw_case_data: Optional[Dict[str, Any]] = None) -> PipelineState:
        TrajectoryLogger.record_step(
            state,
            node_name="SENSE",
            description="Extracting cross-system signals from connected tools and web portals",
        )

        signals: List[ToolSignal] = []

        if raw_case_data:
            # 1. Parse GitHub signals
            for pr in raw_case_data.get("github_prs", []):
                signals.append(ToolSignal(
                    tool_name="github",
                    signal_type="pull_request",
                    entity_id=str(pr.get("id", pr.get("number", "PR"))),
                    title=pr.get("title", ""),
                    status=pr.get("status", "open"),
                    payload=pr,
                ))
            for issue in raw_case_data.get("github_issues", []):
                signals.append(ToolSignal(
                    tool_name="github",
                    signal_type="issue",
                    entity_id=str(issue.get("id", issue.get("number", "ISSUE"))),
                    title=issue.get("title", ""),
                    status=issue.get("status", "open"),
                    payload=issue,
                ))

            # 2. Parse Linear signals
            for ticket in raw_case_data.get("linear_tickets", []):
                signals.append(ToolSignal(
                    tool_name="linear",
                    signal_type="ticket",
                    entity_id=str(ticket.get("id", "LIN")),
                    title=ticket.get("title", ""),
                    status=ticket.get("status", "todo"),
                    payload=ticket,
                ))

            # 3. Parse Sentry signals
            for sentry in raw_case_data.get("sentry_errors", []):
                signals.append(ToolSignal(
                    tool_name="sentry",
                    signal_type="sentry_error",
                    entity_id=str(sentry.get("id", "ERR")),
                    title=sentry.get("title", ""),
                    status=sentry.get("status", "unresolved"),
                    payload=sentry,
                ))

            # 4. Parse Stripe signals
            for stripe in raw_case_data.get("stripe_events", []):
                signals.append(ToolSignal(
                    tool_name="stripe",
                    signal_type="payment_event",
                    entity_id=str(stripe.get("id", "EVT")),
                    title=stripe.get("title", "Stripe Billing Event"),
                    status=stripe.get("status", "active"),
                    payload=stripe,
                ))

            # 5. Extract Web Portal content via Solari Cloud Browser
            for web_target in raw_case_data.get("web_targets", []):
                url = web_target.get("url", "https://app.example.com")
                stealth = web_target.get("stealth", True)
                proxy = web_target.get("proxy", "us")

                browser_res = await self.browser_driver.navigate_and_extract(
                    url=url,
                    stealth=stealth,
                    proxy=proxy,
                    recording=True,
                )

                state.web_extractions.append({
                    "url": browser_res.url,
                    "title": browser_res.title,
                    "status_code": browser_res.status_code,
                    "session_id": browser_res.session_id,
                    "replay_available": browser_res.replay_available,
                })

                signals.append(ToolSignal(
                    tool_name="web_portal",
                    signal_type="web_page",
                    entity_id=url,
                    title=browser_res.title,
                    status="reachable" if browser_res.status_code == 200 else "error",
                    payload={
                        "url": url,
                        "plans": web_target.get("extracted_plans", {}),
                        "snippet": browser_res.content_snippet,
                        "session_id": browser_res.session_id,
                    },
                    raw_snippet=browser_res.content_snippet,
                ))

        state.signals = signals

        TrajectoryLogger.record_step(
            state,
            node_name="SENSE",
            description=f"Extracted {len(signals)} signals across {len(set(s.tool_name for s in signals))} tools",
            data={"signal_count": len(signals), "web_extractions": len(state.web_extractions)},
        )

        return state
