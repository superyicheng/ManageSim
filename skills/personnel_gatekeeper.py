"""Personnel gatekeeper — reviews and approves skill assignments to agents.

Inspired by Edict's libu_hr agent. A gatekeeper ensures agents only get
skills that match their role and the team's needs.
"""

import json
from typing import Optional


class PersonnelGatekeeper:
    def __init__(self, rules: dict = None):
        self.rules = rules or self._default_rules()
        self.pending_approvals = []
        self.decision_log = []

    def _default_rules(self) -> dict:
        """Default skill assignment rules per role."""
        return {
            "leader": {
                "allowed_categories": ["management", "planning", "analysis", "development"],
                "max_skills": 20,
                "auto_approve": True,
            },
            "worker": {
                "allowed_categories": ["development", "testing", "automation", "data"],
                "max_skills": 15,
                "auto_approve": True,
            },
            "reviewer": {
                "allowed_categories": ["analysis", "testing", "security", "quality"],
                "max_skills": 10,
                "auto_approve": True,
            },
            "researcher": {
                "allowed_categories": ["research", "analysis", "data", "documents", "web"],
                "max_skills": 15,
                "auto_approve": True,
            },
        }

    def evaluate_assignment(
        self,
        agent_role: str,
        skill_data: dict,
        current_skill_count: int = 0,
    ) -> dict:
        """Evaluate whether a skill should be assigned to an agent.

        Returns:
            dict with decision (approve/deny/pending), reason, and details
        """
        rules = self.rules.get(agent_role, self.rules.get("worker", {}))

        # Check skill count limit
        max_skills = rules.get("max_skills", 15)
        if current_skill_count >= max_skills:
            decision = {
                "decision": "deny",
                "reason": f"Agent already has {current_skill_count}/{max_skills} skills",
            }
            self.decision_log.append(decision)
            return decision

        # Check category
        skill_tags = skill_data.get("tags", [])
        allowed = rules.get("allowed_categories", [])
        category_match = any(tag in allowed for tag in skill_tags)

        if not category_match and allowed:
            decision = {
                "decision": "pending",
                "reason": f"Skill categories {skill_tags} don't match allowed {allowed} for role {agent_role}",
                "action": "requires_admin_approval",
            }
            self.pending_approvals.append(decision)
            self.decision_log.append(decision)
            return decision

        # Auto-approve if rules allow
        if rules.get("auto_approve", False):
            decision = {
                "decision": "approve",
                "reason": "Auto-approved: matches role requirements",
            }
            self.decision_log.append(decision)
            return decision

        decision = {
            "decision": "pending",
            "reason": "Requires manual approval",
            "action": "requires_admin_approval",
        }
        self.pending_approvals.append(decision)
        self.decision_log.append(decision)
        return decision

    def get_pending_approvals(self) -> list:
        return list(self.pending_approvals)

    def approve_pending(self, index: int) -> dict:
        """Approve a pending skill assignment."""
        if 0 <= index < len(self.pending_approvals):
            approval = self.pending_approvals.pop(index)
            approval["decision"] = "approve"
            approval["reason"] = "Manually approved by admin"
            return approval
        return {"error": "Invalid approval index"}

    def deny_pending(self, index: int, reason: str = "") -> dict:
        """Deny a pending skill assignment."""
        if 0 <= index < len(self.pending_approvals):
            denial = self.pending_approvals.pop(index)
            denial["decision"] = "deny"
            denial["reason"] = reason or "Manually denied by admin"
            return denial
        return {"error": "Invalid approval index"}
