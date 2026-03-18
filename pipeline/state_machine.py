"""Enforced task state machine — inspired by Edict's kanban_update.py."""

import yaml
from pathlib import Path

# Default pipeline (used when no config loaded)
DEFAULT_TRANSITIONS = {
    "Inbox":      {"Triage", "Cancelled"},
    "Triage":     {"Planning", "Cancelled"},
    "Planning":   {"Review", "Cancelled"},
    "Review":     {"Assigned", "Planning", "Cancelled"},
    "Assigned":   {"Executing", "Blocked", "Cancelled"},
    "Executing":  {"QA", "Blocked", "Cancelled"},
    "QA":         {"Done", "Executing", "Cancelled"},
    "Blocked":    {"Executing", "Assigned", "Review", "Cancelled"},
    "Done":       set(),
    "Cancelled":  set(),
}


class StateMachine:
    def __init__(self, pipeline_config=None):
        if pipeline_config:
            self.name = pipeline_config.get("name", "custom")
            self.states = set(pipeline_config.get("states", []))
            self.initial_state = pipeline_config.get("initial_state", "Inbox")
            self.terminal_states = set(pipeline_config.get("terminal_states", ["Done", "Cancelled"]))
            transitions_raw = pipeline_config.get("transitions", {})
            self.transitions = {k: set(v) for k, v in transitions_raw.items()}
        else:
            self.name = "default"
            self.states = set(DEFAULT_TRANSITIONS.keys())
            self.initial_state = "Inbox"
            self.terminal_states = {"Done", "Cancelled"}
            self.transitions = dict(DEFAULT_TRANSITIONS)

    @classmethod
    def from_yaml(cls, path):
        with open(path) as f:
            config = yaml.safe_load(f)
        return cls(config)

    def validate_transition(self, current_state, target_state):
        if current_state not in self.transitions:
            return False, f"Unknown state: {current_state}"
        if current_state in self.terminal_states:
            return False, f"Cannot transition from terminal state: {current_state}"
        allowed = self.transitions[current_state]
        if target_state not in allowed:
            return False, (
                f"Invalid transition: {current_state} → {target_state}. "
                f"Allowed: {sorted(allowed)}"
            )
        return True, "OK"

    def get_allowed_transitions(self, current_state):
        return sorted(self.transitions.get(current_state, set()))

    def is_terminal(self, state):
        return state in self.terminal_states
