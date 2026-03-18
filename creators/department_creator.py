"""Department creator — creates a new project department.

When invoked via Discord (@PersonalAssistant create department "Name"):
1. Creates a new Discord text channel
2. Initializes Easybase tree: server/{project-id}/
3. Creates template soul.md + CLAUDE.md
4. Adds project entry to config
5. Creates initial leader agent
"""

import os
import re
import yaml
from datetime import datetime
from pathlib import Path

# Add parent to path for knowledge imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from knowledge.easybase_bridge import EasybaseBridge
from knowledge.hierarchy_init import (
    init_project, init_team, init_agent,
    init_qa_team, init_error_learning_team,
    init_test_team, init_error_feedback_team,
    init_leader_guide, init_vision,
)


def slugify(name: str) -> str:
    """Convert a name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


class DepartmentCreator:
    def __init__(self, config_path: str = "./config/managesim.yaml", easybase_dir: str = None):
        self.config_path = config_path
        self.bridge = EasybaseBridge(easybase_dir)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if os.path.exists(self.config_path):
            with open(self.config_path) as f:
                return yaml.safe_load(f) or {}
        return {}

    def _save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

    def create_department(
        self,
        name: str,
        channel_id: str = "<pending>",
        bot_token_env: str = "",
        team_template: str = "coding-team",
        pipeline: str = "default",
        stall_threshold: int = 300,
    ) -> dict:
        """Create a new department (project).

        Args:
            name: Human-readable project name
            channel_id: Discord channel ID (set after channel creation)
            bot_token_env: Environment variable name for bot token
            team_template: Team template to use
            pipeline: Pipeline configuration name
            stall_threshold: Stall detection threshold in seconds

        Returns:
            dict with project_id and creation details
        """
        project_id = slugify(name)

        # Check for duplicate
        existing_ids = [p.get("id") for p in self.config.get("projects", [])]
        if project_id in existing_ids:
            return {"error": f"Project '{project_id}' already exists", "project_id": project_id}

        if not bot_token_env:
            bot_token_env = f"DISCORD_BOT_TOKEN_{project_id.upper().replace('-', '_')}"

        # 1. Initialize Easybase tree
        init_project(self.bridge, project_id, name)

        # 2. Create default team
        team_id = f"team-{project_id}-main"
        init_team(self.bridge, project_id, team_id, f"{name} Main Team")

        # 3. Create initial leader agent
        leader_id = f"agent-{project_id}-leader"
        init_agent(
            self.bridge,
            project_id=project_id,
            team_id=team_id,
            agent_id=leader_id,
            agent_name=f"{name} Leader",
            role="leader",
            personality="Strategic and methodical. Makes simple prototypes first, then iterates based on feedback.",
            evolution_goal="Improve decision quality, delegation accuracy, and prototype effectiveness",
        )

        # 4. Create mandatory QA team
        qa_team_id = f"team-{project_id}-qa"
        init_qa_team(self.bridge, project_id, qa_team_id, name)

        # 5. Create mandatory Error-Learning team
        error_team_id = f"team-{project_id}-error-learning"
        init_error_learning_team(self.bridge, project_id, error_team_id, name)

        # 6. Create mandatory Test team
        test_team_id = f"team-{project_id}-test"
        init_test_team(self.bridge, project_id, test_team_id, name)

        # 7. Create mandatory Error Feedback team
        feedback_team_id = f"team-{project_id}-error-feedback"
        init_error_feedback_team(self.bridge, project_id, feedback_team_id, name)

        # 8. Create leader guide for this department
        init_leader_guide(self.bridge, project_id, name)

        # 9. Create vision.md for this department
        init_vision(self.bridge, project_id, name)

        # 7. Add to config
        project_entry = {
            "id": project_id,
            "name": name,
            "discord_channel_id": channel_id,
            "bot_token_env": bot_token_env,
            "team_template": team_template,
            "pipeline": pipeline,
            "soul_template": "templates/project_soul.md",
            "stall_threshold_seconds": stall_threshold,
        }

        if "projects" not in self.config:
            self.config["projects"] = []
        self.config["projects"].append(project_entry)
        self._save_config()

        return {
            "project_id": project_id,
            "name": name,
            "team_id": team_id,
            "leader_id": leader_id,
            "qa_team_id": qa_team_id,
            "error_team_id": error_team_id,
            "test_team_id": test_team_id,
            "feedback_team_id": feedback_team_id,
            "channel_id": channel_id,
            "bot_token_env": bot_token_env,
            "created_at": datetime.utcnow().isoformat(),
            "message": f"Department '{name}' created! Leader, QA, error-learning, test, and error-feedback teams ready.",
        }

    def list_departments(self) -> list:
        """List all configured departments."""
        return self.config.get("projects", [])

    def delete_department(self, project_id: str) -> bool:
        """Remove a department from config (does not delete Easybase data)."""
        projects = self.config.get("projects", [])
        self.config["projects"] = [p for p in projects if p.get("id") != project_id]
        self._save_config()
        return True
