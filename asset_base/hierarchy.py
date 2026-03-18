"""4-level hierarchy management — Server -> Department -> Team -> Agent."""

from .db import Database


class HierarchyManager:
    def __init__(self, db: Database):
        self.db = db

    def get_context(self, level: str, level_id: str = "") -> dict:
        """Get context (soul.md, CLAUDE.md) at any hierarchy level."""
        # Context is stored in Easybase, queried via bridge
        # This returns structured data from SQLite
        if level == "server":
            return {"level": "server", "stats": self._server_stats()}
        elif level == "project":
            return {"level": "project", "id": level_id, "teams": self.db.list_teams(level_id)}
        elif level == "team":
            return {"level": "team", "id": level_id, "agents": self.db.list_agents(team_id=level_id)}
        elif level == "agent":
            return {"level": "agent", "id": level_id, "detail": self.db.get_agent(level_id)}
        return {}

    def _server_stats(self) -> dict:
        """Aggregate server-level statistics."""
        return {
            "total_tasks": self.db.get_stat("total_tasks") or 0,
            "total_agents": self.db.get_stat("total_agents") or 0,
            "total_cost": self.db.get_stat("total_cost") or 0.0,
        }

    def get_agent_hierarchy(self, agent_id: str) -> dict:
        """Get the full hierarchy path for an agent."""
        agent = self.db.get_agent(agent_id)
        if not agent:
            return {}
        team = self.db.get_team(agent["team_id"])
        return {
            "server": "server",
            "project": agent["project_id"],
            "team": agent["team_id"],
            "team_name": team["name"] if team else "",
            "agent": agent_id,
            "agent_name": agent["name"],
            "role": agent["role"],
        }
