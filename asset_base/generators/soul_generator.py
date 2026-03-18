"""Auto-generate soul.md from agent history."""


def generate_soul_from_history(agent_data: dict, task_history: list) -> str:
    """Generate a soul.md based on an agent's task history and performance."""
    name = agent_data.get("name", "Agent")
    role = agent_data.get("role", "worker")
    goal = agent_data.get("evolution_goal", "")
    success_rate = agent_data.get("success_rate", 0.0)
    tasks_completed = agent_data.get("tasks_completed", 0)

    lines = [
        f"# {name}",
        "",
        "## Identity",
        f"{role.title()} agent with {tasks_completed} tasks completed.",
        f"Success rate: {success_rate:.0%}.",
        "",
        "## Evolution Goal",
        goal or "Continuous improvement in task execution.",
        "",
        "## Strengths",
    ]

    if success_rate > 0.8:
        lines.append("- High reliability and task completion rate")
    if tasks_completed > 10:
        lines.append("- Experienced with multiple task types")

    lines.extend([
        "",
        "## Areas for Improvement",
        "- To be identified through evolution cycles",
    ])

    return "\n".join(lines)
