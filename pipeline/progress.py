"""Structured progress protocol — machine-parseable progress reporting."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ProgressStep:
    number: int
    name: str
    status: str = "pending"  # pending | active | done

    def to_string(self):
        return f"{self.number}.{self.name}:{self.status}"

    @classmethod
    def from_string(cls, s):
        parts = s.split(":")
        name_parts = parts[0].split(".", 1)
        number = int(name_parts[0]) if name_parts[0].isdigit() else 0
        name = name_parts[1] if len(name_parts) > 1 else name_parts[0]
        status = parts[1] if len(parts) > 1 else "pending"
        return cls(number=number, name=name, status=status)


@dataclass
class ProgressReport:
    task_id: str
    text: str
    steps: list[ProgressStep] = field(default_factory=list)
    tokens: int = 0
    cost: float = 0.0
    elapsed: float = 0.0
    agent_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def checklist_string(self):
        return "|".join(s.to_string() for s in self.steps)

    @classmethod
    def from_checklist_string(cls, task_id, text, checklist, **kwargs):
        steps = [ProgressStep.from_string(s) for s in checklist.split("|") if s.strip()]
        return cls(task_id=task_id, text=text, steps=steps, **kwargs)

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "text": self.text,
            "checklist": self.checklist_string(),
            "tokens": self.tokens,
            "cost": self.cost,
            "elapsed": self.elapsed,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
        }


class ProgressTracker:
    def __init__(self):
        self.reports = {}  # task_id -> list of ProgressReport

    def record(self, report: ProgressReport):
        if report.task_id not in self.reports:
            self.reports[report.task_id] = []
        self.reports[report.task_id].append(report)

    def latest(self, task_id):
        reports = self.reports.get(task_id, [])
        return reports[-1] if reports else None

    def all_reports(self, task_id):
        return self.reports.get(task_id, [])

    def time_since_last(self, task_id):
        latest = self.latest(task_id)
        if not latest:
            return None
        last_time = datetime.fromisoformat(latest.timestamp)
        return (datetime.utcnow() - last_time).total_seconds()
