"""Mandatory review gate — 4-axis evaluation before execution."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ReviewVerdict(str, Enum):
    APPROVE = "approve"
    VETO = "veto"


class ReviewAxis(str, Enum):
    FEASIBILITY = "feasibility"
    COMPLETENESS = "completeness"
    RISK = "risk"
    RESOURCES = "resources"
    TEST_COVERAGE = "test_coverage"
    STRUCTURAL_FIT = "structural_fit"
    REGRESSION_RISK = "regression_risk"


@dataclass
class AxisScore:
    axis: ReviewAxis
    score: float  # 0.0 to 1.0
    notes: str = ""


@dataclass
class ReviewResult:
    verdict: ReviewVerdict
    round_number: int
    axes: list[AxisScore] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    reviewer_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self):
        return {
            "verdict": self.verdict.value,
            "round": self.round_number,
            "axes": [{"axis": a.axis.value, "score": a.score, "notes": a.notes} for a in self.axes],
            "improvements": self.improvements,
            "reviewer_id": self.reviewer_id,
            "timestamp": self.timestamp,
        }


class ReviewGate:
    def __init__(self, max_rounds=3, enabled=True, axes=None):
        self.max_rounds = max_rounds
        self.enabled = enabled
        self.axes = axes or [a.value for a in ReviewAxis]
        self.reviews = {}  # task_id -> list of ReviewResult

    @classmethod
    def from_pipeline_config(cls, pipeline_config):
        gate_config = pipeline_config.get("review_gate", {})
        return cls(
            max_rounds=gate_config.get("max_rounds", 3),
            enabled=gate_config.get("enabled", True),
            axes=gate_config.get("axes"),
        )

    def submit_review(self, task_id, result: ReviewResult):
        if task_id not in self.reviews:
            self.reviews[task_id] = []
        self.reviews[task_id].append(result)
        # Force approve on max round
        if result.round_number >= self.max_rounds and result.verdict == ReviewVerdict.VETO:
            result.verdict = ReviewVerdict.APPROVE
            result.improvements.append("[AUTO] Forced approval at max review round")
        return result

    def get_review_history(self, task_id):
        return self.reviews.get(task_id, [])

    def current_round(self, task_id):
        return len(self.reviews.get(task_id, [])) + 1

    def is_approved(self, task_id):
        history = self.reviews.get(task_id, [])
        if not history:
            return False
        return history[-1].verdict == ReviewVerdict.APPROVE
