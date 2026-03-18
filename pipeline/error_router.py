"""Error routing — routes errors to responsible agents based on error type.

Error types:
- decision: Wrong task assignment, bad plan → routed to LEADER
- execution: Bugs, incomplete work → routed to WORKER who executed
- review: Missed defects in review → routed to REVIEWER
- integration: Doesn't fit overall structure → routed to LEADER + WORKER
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ErrorType(str, Enum):
    DECISION = "decision"
    EXECUTION = "execution"
    REVIEW = "review"
    INTEGRATION = "integration"


class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorStatus(str, Enum):
    OPEN = "open"
    ANALYZING = "analyzing"
    RESOLVED = "resolved"


@dataclass
class ErrorReport:
    id: str
    task_id: str
    project_id: str
    error_type: ErrorType
    responsible_agent: str
    responsible_role: str
    description: str = ""
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    root_cause: str = ""
    lesson_learned: str = ""
    status: ErrorStatus = ErrorStatus.OPEN
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "error_type": self.error_type.value,
            "responsible_agent": self.responsible_agent,
            "responsible_role": self.responsible_role,
            "description": self.description,
            "severity": self.severity.value,
            "root_cause": self.root_cause,
            "lesson_learned": self.lesson_learned,
            "status": self.status.value,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }


# Routing rules: error_type -> list of target roles
ROUTING_RULES = {
    ErrorType.DECISION: ["leader"],
    ErrorType.EXECUTION: ["worker"],
    ErrorType.REVIEW: ["reviewer"],
    ErrorType.INTEGRATION: ["leader", "worker"],
}


class ErrorRouter:
    """Routes errors to responsible agents based on error type."""

    def __init__(self):
        self.reports = {}  # report_id -> ErrorReport

    def route_error(self, error_report: ErrorReport) -> list[str]:
        """Determine target roles for an error report.

        Returns list of roles that should receive this error.
        """
        return ROUTING_RULES.get(error_report.error_type, ["leader"])

    def create_report(
        self,
        task_id: str,
        project_id: str,
        error_type: str,
        responsible_agent: str,
        responsible_role: str,
        description: str = "",
        severity: str = "medium",
    ) -> ErrorReport:
        """Create a new error report and route it."""
        report_id = f"ERR-{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        report = ErrorReport(
            id=report_id,
            task_id=task_id,
            project_id=project_id,
            error_type=ErrorType(error_type),
            responsible_agent=responsible_agent,
            responsible_role=responsible_role,
            description=description,
            severity=ErrorSeverity(severity),
        )

        self.reports[report_id] = report
        targets = self.route_error(report)

        return report

    def resolve_error(
        self,
        report_id: str,
        root_cause: str,
        lesson_learned: str,
    ) -> Optional[ErrorReport]:
        """Resolve an error with root cause analysis and lesson learned."""
        report = self.reports.get(report_id)
        if not report:
            return None

        report.root_cause = root_cause
        report.lesson_learned = lesson_learned
        report.status = ErrorStatus.RESOLVED
        report.resolved_at = datetime.now(timezone.utc).isoformat()

        return report

    def get_errors_for_agent(self, agent_id: str) -> list[ErrorReport]:
        """Get all error reports for a specific agent."""
        return [r for r in self.reports.values() if r.responsible_agent == agent_id]

    def get_open_errors(self, project_id: str = None) -> list[ErrorReport]:
        """Get all open (unresolved) error reports."""
        errors = [r for r in self.reports.values() if r.status != ErrorStatus.RESOLVED]
        if project_id:
            errors = [r for r in errors if r.project_id == project_id]
        return errors
