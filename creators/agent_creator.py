"""Agent creator — initializes new agents with full configuration.

Creates:
- soul.md with role, personality, evolution goal
- CLAUDE.md with pipeline role, permissions, protocols
- Initial PersonalityState based on role archetype
- Initial Genes based on evolution goal
- Registration in Asset Base
"""

import os
import json
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from knowledge.easybase_bridge import EasybaseBridge
from knowledge.hierarchy_init import init_agent

# Role archetypes with default personality states
ROLE_ARCHETYPES = {
    "leader": {
        "personality": "Strategic and decisive. Evaluates options before committing. Communicates plans clearly.",
        "evolution_goal": "Improve decision quality, resource allocation, and delegation accuracy",
        "personality_state": {
            "rigor": 0.80, "creativity": 0.50, "verbosity": 0.40,
            "risk_tolerance": 0.45, "obedience": 0.70,
        },
        "pipeline_role": "PLANNER",
        "can_report_to": ["coordinator"],
        "can_delegate_to": ["reviewer", "worker"],
    },
    "worker": {
        "personality": "Focused and efficient. Follows instructions precisely. Reports progress regularly.",
        "evolution_goal": "Improve execution efficiency, search quality, and task completion rate",
        "personality_state": {
            "rigor": 0.90, "creativity": 0.20, "verbosity": 0.20,
            "risk_tolerance": 0.25, "obedience": 0.90,
        },
        "pipeline_role": "WORKER",
        "can_report_to": ["dispatcher", "leader"],
        "can_delegate_to": [],
    },
    "reviewer": {
        "personality": "Thorough and analytical. Questions assumptions. Provides constructive feedback.",
        "evolution_goal": "Improve review thoroughness and defect detection rate",
        "personality_state": {
            "rigor": 0.90, "creativity": 0.30, "verbosity": 0.50,
            "risk_tolerance": 0.20, "obedience": 0.85,
        },
        "pipeline_role": "REVIEWER",
        "can_report_to": ["leader"],
        "can_delegate_to": ["planner"],
    },
    "researcher": {
        "personality": "Curious and methodical. Explores broadly, then focuses deeply. Documents findings thoroughly.",
        "evolution_goal": "Improve information coverage, source quality, and synthesis accuracy",
        "personality_state": {
            "rigor": 0.75, "creativity": 0.60, "verbosity": 0.50,
            "risk_tolerance": 0.50, "obedience": 0.65,
        },
        "pipeline_role": "RESEARCHER",
        "can_report_to": ["leader", "synthesizer"],
        "can_delegate_to": [],
    },
    "qa_tester": {
        "personality": "Meticulous and systematic. Tests everything against the whole project. Never assumes something works without proof.",
        "evolution_goal": "Improve test coverage, regression detection, and structural integrity checking",
        "personality_state": {
            "rigor": 0.95, "creativity": 0.15, "verbosity": 0.40,
            "risk_tolerance": 0.10, "obedience": 0.85,
        },
        "pipeline_role": "QA_TESTER",
        "can_report_to": ["leader", "error_analyst"],
        "can_delegate_to": [],
    },
    "error_analyst": {
        "personality": "Analytical and thorough. Traces errors to root causes. Turns failures into lasting knowledge.",
        "evolution_goal": "Improve root cause analysis accuracy, error pattern recognition, and knowledge transfer effectiveness",
        "personality_state": {
            "rigor": 0.90, "creativity": 0.40, "verbosity": 0.60,
            "risk_tolerance": 0.20, "obedience": 0.75,
        },
        "pipeline_role": "ERROR_ANALYST",
        "can_report_to": ["leader"],
        "can_delegate_to": [],
    },
}


class AgentCreator:
    def __init__(self, easybase_dir: str = None, asset_base_url: str = "http://localhost:8100"):
        self.bridge = EasybaseBridge(easybase_dir)
        self.asset_base_url = asset_base_url

    def create_agent(
        self,
        project_id: str,
        team_id: str,
        name: str,
        role: str = "worker",
        goal: str = "",
        task: str = "",
        personality: str = "",
    ) -> dict:
        """Create a new agent with full configuration.

        Args:
            project_id: Project this agent belongs to
            team_id: Team this agent belongs to
            name: Human-readable agent name
            role: Agent role (leader, worker, reviewer, researcher)
            goal: Evolution goal (what the agent should improve at)
            task: Initial task assignment
            personality: Custom personality (uses archetype default if empty)

        Returns:
            dict with agent_id and creation details
        """
        # Generate agent ID
        agent_id = f"agent-{project_id}-{name.lower().replace(' ', '-')}"

        # Get archetype
        archetype = ROLE_ARCHETYPES.get(role, ROLE_ARCHETYPES["worker"])

        # Use provided or default values
        final_personality = personality or archetype["personality"]
        final_goal = goal or archetype["evolution_goal"]
        personality_state = archetype["personality_state"]

        # 1. Create soul.md in Easybase
        init_agent(
            self.bridge,
            project_id=project_id,
            team_id=team_id,
            agent_id=agent_id,
            agent_name=name,
            role=role,
            personality=final_personality,
            evolution_goal=final_goal,
        )

        # 2. Create CLAUDE.md in Easybase
        claude_content = self._generate_claude_md(agent_id, role, archetype, task)
        self.bridge.store_chunk(
            chunk_id=f"claude-{agent_id}",
            summary=f"Behavior instructions for {name} ({role})",
            body=claude_content,
            domain="context",
            tags=f"claude, agent, {agent_id}, {role}, behavior",
            tree_path=f"server/{project_id}/{team_id}/{agent_id}",
            stored_by="system",
            stored_by_type="system",
            channel_origin=project_id,
            visibility="agent",
        )

        # 3. Register in Asset Base (best-effort)
        self._register_in_asset_base(agent_id, name, project_id, team_id, role, final_goal, personality_state)

        return {
            "agent_id": agent_id,
            "name": name,
            "role": role,
            "project_id": project_id,
            "team_id": team_id,
            "evolution_goal": final_goal,
            "personality_state": personality_state,
            "task": task,
            "created_at": datetime.utcnow().isoformat(),
            "message": f"Agent '{name}' ({role}) created and ready for work.",
        }

    def _generate_claude_md(self, agent_id: str, role: str, archetype: dict, task: str) -> str:
        """Generate CLAUDE.md content for an agent."""
        lines = [
            f"# Agent Behavior Instructions — {agent_id}",
            "",
            f"## Pipeline Role: {archetype['pipeline_role']} ({role})",
            "",
            "## Permissions",
            f"- can_report_to: {archetype['can_report_to']}",
            f"- can_delegate_to: {archetype['can_delegate_to']}",
            "",
            "## Progress Protocol",
            f"managesim-task progress {{task_id}} \"{{status}}\" \"{{checklist}}\" --agent {agent_id}",
            "",
            "## Completion Protocol",
            f"managesim-task done {{task_id}} \"{{summary}}\" --agent {agent_id}",
            "",
            "## Rules",
            "1. Always use managesim-task CLI for task operations",
            "2. Report progress at every key step",
            "3. Respect permission matrix — only communicate with allowed roles",
            "4. Store knowledge with proper provenance metadata",
            "5. Follow the assigned pipeline strictly",
        ]

        if task:
            lines.extend([
                "",
                "## Current Task",
                task,
            ])

        return "\n".join(lines)

    def _register_in_asset_base(self, agent_id, name, project_id, team_id, role, goal, personality_state):
        """Register agent in Asset Base SQLite database."""
        try:
            import requests
            requests.post(f"{self.asset_base_url}/api/agents", json={
                "id": agent_id,
                "name": name,
                "project_id": project_id,
                "team_id": team_id,
                "role": role,
                "status": "active",
                "evolution_goal": goal,
                "personality_state": json.dumps(personality_state),
                "created_at": datetime.utcnow().isoformat(),
            }, timeout=5)
        except Exception:
            pass  # Registration is best-effort

    def list_archetypes(self) -> dict:
        """List available role archetypes."""
        return {role: {
            "personality": arch["personality"],
            "evolution_goal": arch["evolution_goal"],
            "pipeline_role": arch["pipeline_role"],
        } for role, arch in ROLE_ARCHETYPES.items()}
