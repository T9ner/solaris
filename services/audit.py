"""Domain service for cross-system gap detection and correlation analysis.

Identifies:
1. Status drift between issue trackers (Linear) and source control (GitHub).
2. Untracked production errors in Sentry missing tickets in Linear/Jira.
3. Live web deployment mismatches (e.g. pricing page differs from Stripe API).
4. Release regressions between merged PRs and customer incident logs.
"""

from typing import List
from agents.state import ToolSignal, DiscrepancyReport


class CrossSystemAuditService:
    """Core reasoning engine for identifying cross-tool discrepancies."""

    @staticmethod
    def audit_signals(signals: List[ToolSignal]) -> List[DiscrepancyReport]:
        discrepancies: List[DiscrepancyReport] = []

        # Index signals by tool and entity
        github_prs = [s for s in signals if s.tool_name == "github" and s.signal_type == "pull_request"]
        github_issues = [s for s in signals if s.tool_name == "github" and s.signal_type == "issue"]
        linear_tickets = [s for s in signals if s.tool_name == "linear"]
        sentry_errors = [s for s in signals if s.tool_name == "sentry"]
        stripe_events = [s for s in signals if s.tool_name == "stripe"]
        web_pages = [s for s in signals if s.tool_name == "web_portal"]

        # 1. Detect PR merged vs Linear Ticket In Progress / Todo
        for pr in github_prs:
            if pr.status in ("merged", "closed"):
                # Find matching linear ticket by reference or title keyword
                for ticket in linear_tickets:
                    linked = (
                        pr.payload.get("linear_issue_id") == ticket.entity_id
                        or ticket.entity_id.lower() in pr.title.lower()
                        or ticket.title.lower() in pr.title.lower()
                    )
                    if linked and ticket.status in ("in_progress", "todo", "unstarted"):
                        discrepancies.append(DiscrepancyReport(
                            gap_id=f"gap_drift_{pr.entity_id}_{ticket.entity_id}",
                            category="status_drift",
                            severity="high",
                            title=f"Merged PR #{pr.entity_id} with open Linear ticket {ticket.entity_id}",
                            description=(
                                f"GitHub PR #{pr.entity_id} ('{pr.title}') was merged, "
                                f"but Linear ticket {ticket.entity_id} remains marked as '{ticket.status}'."
                            ),
                            affected_tools=["github", "linear"],
                            evidence={
                                "github_pr": pr.entity_id,
                                "pr_status": pr.status,
                                "linear_ticket": ticket.entity_id,
                                "ticket_status": ticket.status,
                            },
                            recommended_action=f"Update Linear ticket {ticket.entity_id} status to 'Done' and log release note.",
                        ))

        # 2. Detect Linear ticket marked Done but Critical GitHub Issues still open
        for ticket in linear_tickets:
            if ticket.status == "done":
                for issue in github_issues:
                    linked = (
                        ticket.entity_id.lower() in issue.title.lower()
                        or issue.payload.get("linear_ticket") == ticket.entity_id
                    )
                    if linked and issue.status == "open" and issue.payload.get("severity") in ("critical", "high"):
                        discrepancies.append(DiscrepancyReport(
                            gap_id=f"gap_open_bug_{ticket.entity_id}_{issue.entity_id}",
                            category="untracked_bug",
                            severity="critical",
                            title=f"Completed ticket {ticket.entity_id} has unresolved critical bug #{issue.entity_id}",
                            description=(
                                f"Linear ticket {ticket.entity_id} was closed as Done, but critical GitHub issue "
                                f"#{issue.entity_id} ('{issue.title}') remains open."
                            ),
                            affected_tools=["linear", "github"],
                            evidence={
                                "linear_ticket": ticket.entity_id,
                                "github_issue": issue.entity_id,
                                "issue_title": issue.title,
                            },
                            recommended_action=f"Reopen Linear ticket or spawn a Solari microVM sandbox to reproduce and patch issue #{issue.entity_id}.",
                        ))

        # 3. Detect high-frequency Sentry errors without tracking tickets
        for sentry in sentry_errors:
            error_count = sentry.payload.get("event_count", 1)
            is_handled = sentry.payload.get("has_ticket", False)
            if error_count >= 10 and not is_handled:
                discrepancies.append(DiscrepancyReport(
                    gap_id=f"gap_sentry_{sentry.entity_id}",
                    category="release_regression",
                    severity="critical" if error_count > 50 else "high",
                    title=f"Unresolved production exception '{sentry.title}' occurring {error_count} times",
                    description=(
                        f"Sentry error '{sentry.title}' has occurred {error_count} times since last deployment, "
                        f"with no tracking ticket in Linear."
                    ),
                    affected_tools=["sentry", "linear"],
                    evidence={
                        "sentry_id": sentry.entity_id,
                        "event_count": error_count,
                        "stacktrace": sentry.payload.get("stacktrace", ""),
                    },
                    recommended_action="Create hotfix branch in sandbox, reproduce stacktrace in Python kernel, and deploy patch.",
                ))

        # 4. Detect Stripe pricing mismatches against public web portal
        for page in web_pages:
            web_pricing = page.payload.get("plans", {})
            for event in stripe_events:
                stripe_pricing = event.payload.get("plans", {})
                for plan_name, stripe_price in stripe_pricing.items():
                    if plan_name in web_pricing and web_pricing[plan_name] != stripe_price:
                        discrepancies.append(DiscrepancyReport(
                            gap_id=f"gap_price_{plan_name}",
                            category="payment_mismatch",
                            severity="high",
                            title=f"Pricing drift for {plan_name}: Web (${web_pricing[plan_name]}) vs Stripe (${stripe_price})",
                            description=(
                                f"Live marketing page displays ${web_pricing[plan_name]} for {plan_name}, "
                                f"while Stripe API billing tier is configured at ${stripe_price}."
                            ),
                            affected_tools=["web_portal", "stripe"],
                            evidence={
                                "plan": plan_name,
                                "web_price": web_pricing[plan_name],
                                "stripe_price": stripe_price,
                                "page_url": page.payload.get("url", ""),
                            },
                            recommended_action=f"Synchronize Stripe price object for '{plan_name}' to match published ${web_pricing[plan_name]} pricing.",
                        ))

        return discrepancies
