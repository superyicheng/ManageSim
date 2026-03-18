"""Agent-to-agent permission matrix enforcement."""

import yaml
from datetime import datetime


class PermissionMatrix:
    def __init__(self, permissions_config=None):
        self.permissions = permissions_config or {}
        self.violations = []

    @classmethod
    def from_pipeline_config(cls, pipeline_config):
        perms = pipeline_config.get("permissions", {})
        return cls(perms)

    def can_communicate(self, from_role, to_role):
        allowed = self.permissions.get(from_role, [])
        return to_role in allowed

    def check_and_log(self, from_role, to_role, task_id=None):
        if self.can_communicate(from_role, to_role):
            return True
        violation = {
            "timestamp": datetime.utcnow().isoformat(),
            "from_role": from_role,
            "to_role": to_role,
            "task_id": task_id,
            "message": f"Permission denied: {from_role} cannot communicate with {to_role}"
        }
        self.violations.append(violation)
        return False

    def get_allowed_targets(self, role):
        return list(self.permissions.get(role, []))

    def get_violations(self):
        return list(self.violations)
