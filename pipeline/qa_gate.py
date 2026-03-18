"""QA Gate — QA-specific validation extending the review gate pattern.

The QA gate validates completed work against 4 axes:
1. Correctness — Does the output have errors?
2. Structural Fit — Does it fit the project structure?
3. Regression — Does it break existing functionality?
4. Vision Alignment — Does it align with vision.md?
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class QAVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"


class QAAxis(str, Enum):
    CORRECTNESS = "correctness"
    STRUCTURAL_FIT = "structural_fit"
    REGRESSION = "regression"
    VISION_ALIGNMENT = "vision_alignment"


@dataclass
class QAAxisScore:
    axis: QAAxis
    passed: bool
    notes: str = ""


@dataclass
class QAResult:
    task_id: str
    project_id: str
    verdict: QAVerdict
    axes: list[QAAxisScore] = field(default_factory=list)
    defects: list[str] = field(default_factory=list)
    tester_agent: str = ""
    test_coverage: str = ""
    structural_notes: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "project_id": self.project_id,
            "verdict": self.verdict.value,
            "axes": [{"axis": a.axis.value, "passed": a.passed, "notes": a.notes} for a in self.axes],
            "defects": self.defects,
            "tester_agent": self.tester_agent,
            "test_coverage": self.test_coverage,
            "structural_notes": self.structural_notes,
            "timestamp": self.timestamp,
        }


class QAGate:
    """QA-specific validation gate for completed work."""

    def __init__(self, required_axes=None):
        self.required_axes = required_axes or [a.value for a in QAAxis]
        self.results = {}  # task_id -> list of QAResult

    def submit_result(self, result: QAResult) -> QAResult:
        """Submit a QA test result for a task."""
        if result.task_id not in self.results:
            self.results[result.task_id] = []
        self.results[result.task_id].append(result)
        return result

    def is_passed(self, task_id: str) -> bool:
        """Check if a task has passed QA."""
        history = self.results.get(task_id, [])
        if not history:
            return False
        return history[-1].verdict == QAVerdict.PASS

    def get_defects(self, task_id: str) -> list[str]:
        """Get all defects found for a task across all QA rounds."""
        defects = []
        for result in self.results.get(task_id, []):
            defects.extend(result.defects)
        return defects

    def get_history(self, task_id: str) -> list[QAResult]:
        """Get all QA results for a task."""
        return self.results.get(task_id, [])

    def evaluate(
        self,
        task_id: str,
        project_id: str,
        axis_scores: list[QAAxisScore],
        defects: list[str] = None,
        tester_agent: str = "",
        test_coverage: str = "",
        structural_notes: str = "",
    ) -> QAResult:
        """Evaluate a task and create a QA result.

        If any required axis fails, the overall verdict is FAIL.
        """
        all_passed = all(a.passed for a in axis_scores)
        has_defects = bool(defects)

        if all_passed and not has_defects:
            verdict = QAVerdict.PASS
        elif has_defects:
            verdict = QAVerdict.FAIL
        else:
            verdict = QAVerdict.CONDITIONAL

        result = QAResult(
            task_id=task_id,
            project_id=project_id,
            verdict=verdict,
            axes=axis_scores,
            defects=defects or [],
            tester_agent=tester_agent,
            test_coverage=test_coverage,
            structural_notes=structural_notes,
        )

        return self.submit_result(result)
