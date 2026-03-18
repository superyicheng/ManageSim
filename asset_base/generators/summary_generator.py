"""Auto-generate _summary.md files for Easybase tree nodes."""


def generate_project_summary(project_data: dict, teams: list, task_stats: dict) -> str:
    """Generate a summary for a project node."""
    name = project_data.get("name", "Project")
    lines = [
        f"# {name} — Summary",
        "",
        f"**Teams:** {len(teams)}",
        f"**Tasks completed:** {task_stats.get('completed', 0)}",
        f"**Active tasks:** {task_stats.get('active', 0)}",
        "",
        "## Teams",
    ]
    for team in teams:
        lines.append(f"- **{team.get('name', team.get('id', '?'))}**: {team.get('agent_count', 0)} agents")

    return "\n".join(lines)


def generate_team_summary(team_data: dict, agents: list) -> str:
    """Generate a summary for a team node."""
    name = team_data.get("name", "Team")
    lines = [
        f"# {name} — Summary",
        "",
        f"**Agents:** {len(agents)}",
        "",
        "## Agents",
    ]
    for agent in agents:
        lines.append(f"- **{agent.get('name', '?')}** ({agent.get('role', 'worker')}): {agent.get('status', 'unknown')}")

    return "\n".join(lines)
