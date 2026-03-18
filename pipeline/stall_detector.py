"""Stall detection with 4-phase auto-recovery."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class RecoveryPhase(int, Enum):
    REDISPATCH = 1       # T+5min: re-dispatch to same agent
    ESCALATE_LEAD = 2    # T+10min: escalate to team lead
    ESCALATE_COORD = 3   # T+15min: escalate to project coordinator
    AUTO_ROLLBACK = 4    # T+20min: rollback + re-dispatch


DEFAULT_PHASE_THRESHOLDS = {
    RecoveryPhase.REDISPATCH: 300,       # 5 minutes
    RecoveryPhase.ESCALATE_LEAD: 600,    # 10 minutes
    RecoveryPhase.ESCALATE_COORD: 900,   # 15 minutes
    RecoveryPhase.AUTO_ROLLBACK: 1200,   # 20 minutes
}


@dataclass
class StallEvent:
    task_id: str
    phase: RecoveryPhase
    action_taken: str
    agent_id: str
    timestamp: str
    stall_duration_seconds: float


class StallDetector:
    def __init__(self, threshold_seconds=300, phase_thresholds=None):
        self.base_threshold = threshold_seconds
        self.phase_thresholds = phase_thresholds or DEFAULT_PHASE_THRESHOLDS
        self.stall_history = {}  # task_id -> list of StallEvent
        self.last_progress = {}  # task_id -> datetime

    def record_progress(self, task_id):
        self.last_progress[task_id] = datetime.utcnow()

    def check_stall(self, task_id):
        last = self.last_progress.get(task_id)
        if not last:
            return None
        elapsed = (datetime.utcnow() - last).total_seconds()
        if elapsed < self.base_threshold:
            return None
        # Determine recovery phase
        for phase in reversed(list(RecoveryPhase)):
            if elapsed >= self.phase_thresholds[phase]:
                return phase
        return None

    def get_recovery_action(self, phase):
        actions = {
            RecoveryPhase.REDISPATCH: "Re-dispatch task to same agent",
            RecoveryPhase.ESCALATE_LEAD: "Escalate to team lead",
            RecoveryPhase.ESCALATE_COORD: "Escalate to project coordinator",
            RecoveryPhase.AUTO_ROLLBACK: "Auto-rollback to last checkpoint and re-dispatch",
        }
        return actions.get(phase, "Unknown recovery action")

    def record_stall_event(self, task_id, phase, agent_id):
        event = StallEvent(
            task_id=task_id,
            phase=phase,
            action_taken=self.get_recovery_action(phase),
            agent_id=agent_id,
            timestamp=datetime.utcnow().isoformat(),
            stall_duration_seconds=(datetime.utcnow() - self.last_progress.get(task_id, datetime.utcnow())).total_seconds(),
        )
        if task_id not in self.stall_history:
            self.stall_history[task_id] = []
        self.stall_history[task_id].append(event)

        # At Phase 2+ (escalation), also create an error report for the stalled agent
        if phase.value >= RecoveryPhase.ESCALATE_LEAD.value:
            event.error_report = {
                "error_type": "execution",
                "responsible_agent": agent_id,
                "responsible_role": "worker",
                "description": f"Task {task_id} stalled at phase {phase.name} after {event.stall_duration_seconds:.0f}s",
                "severity": "high" if phase.value >= RecoveryPhase.ESCALATE_COORD.value else "medium",
            }

        return event
