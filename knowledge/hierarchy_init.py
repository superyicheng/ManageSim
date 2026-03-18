"""Bootstrap the 4-level Easybase tree structure with template soul.md/CLAUDE.md."""

import os
import yaml
from pathlib import Path
from .easybase_bridge import EasybaseBridge


TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _load_template(name):
    path = os.path.join(TEMPLATES_DIR, name)
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return f"# {name}\n\nTemplate not found."


def init_server(bridge: EasybaseBridge, server_name: str = "My Agent Server"):
    """Initialize server-level chunks."""
    soul_content = _load_template("server_soul.md").replace("{{SERVER_NAME}}", server_name)

    bridge.store_chunk(
        chunk_id="server-soul",
        summary=f"Server identity and mission for {server_name}",
        body=soul_content,
        domain="context",
        tags="soul, server, identity, mission",
        tree_path="server",
        stored_by="system",
        stored_by_type="system",
        visibility="public",
    )

    claude_content = _load_template("server_claude.md").replace("{{SERVER_NAME}}", server_name)

    bridge.store_chunk(
        chunk_id="server-claude",
        summary=f"Global AI behavior rules for {server_name}",
        body=claude_content,
        domain="context",
        tags="claude, server, behavior, rules",
        tree_path="server",
        stored_by="system",
        stored_by_type="system",
        visibility="public",
    )


def init_project(bridge: EasybaseBridge, project_id: str, project_name: str):
    """Initialize project-level (department) chunks."""
    soul_content = _load_template("project_soul.md").replace(
        "{{PROJECT_NAME}}", project_name
    ).replace("{{PROJECT_ID}}", project_id)

    bridge.store_chunk(
        chunk_id=f"soul-{project_id}",
        summary=f"Project identity for {project_name}",
        body=soul_content,
        domain="context",
        tags=f"soul, project, {project_id}, identity",
        tree_path=f"server/{project_id}",
        stored_by="system",
        stored_by_type="system",
        channel_origin=project_id,
        visibility="project",
    )


def init_team(bridge: EasybaseBridge, project_id: str, team_id: str, team_name: str = ""):
    """Initialize team-level chunks."""
    display_name = team_name or team_id
    context_content = _load_template("team_context.md").replace(
        "{{TEAM_NAME}}", display_name
    ).replace("{{TEAM_ID}}", team_id).replace("{{PROJECT_ID}}", project_id)

    bridge.store_chunk(
        chunk_id=f"context-{team_id}",
        summary=f"Team context for {display_name}",
        body=context_content,
        domain="context",
        tags=f"context, team, {team_id}, {project_id}",
        tree_path=f"server/{project_id}/{team_id}",
        stored_by="system",
        stored_by_type="system",
        channel_origin=project_id,
        visibility="team",
    )


def init_agent(
    bridge: EasybaseBridge,
    project_id: str,
    team_id: str,
    agent_id: str,
    agent_name: str = "",
    role: str = "worker",
    personality: str = "",
    evolution_goal: str = "",
):
    """Initialize agent-level chunks."""
    display_name = agent_name or agent_id
    soul_content = _load_template("agent_soul.md").replace(
        "{{AGENT_NAME}}", display_name
    ).replace("{{AGENT_ID}}", agent_id).replace(
        "{{ROLE}}", role
    ).replace("{{PERSONALITY}}", personality or "Focused and methodical.").replace(
        "{{EVOLUTION_GOAL}}", evolution_goal or "Improve task execution quality"
    )

    tree_path = f"server/{project_id}/{team_id}/{agent_id}"

    bridge.store_chunk(
        chunk_id=f"soul-{agent_id}",
        summary=f"Agent identity for {display_name} ({role})",
        body=soul_content,
        domain="context",
        tags=f"soul, agent, {agent_id}, {role}, {project_id}",
        tree_path=tree_path,
        stored_by="system",
        stored_by_type="system",
        channel_origin=project_id,
        visibility="agent",
    )


def init_qa_team(bridge: EasybaseBridge, project_id: str, team_id: str, project_name: str = ""):
    """Initialize QA team with a qa_tester agent."""
    display_name = project_name or project_id
    init_team(bridge, project_id, team_id, f"{display_name} QA Team")

    qa_agent_id = f"agent-{project_id}-qa-tester"
    init_agent(
        bridge,
        project_id=project_id,
        team_id=team_id,
        agent_id=qa_agent_id,
        agent_name=f"{display_name} QA Tester",
        role="qa_tester",
        personality="Meticulous and systematic. Tests everything against the whole project. Never assumes something works without proof.",
        evolution_goal="Improve test coverage, regression detection, and structural integrity checking",
    )


def init_error_learning_team(bridge: EasybaseBridge, project_id: str, team_id: str, project_name: str = ""):
    """Initialize error-learning team with an error_analyst agent."""
    display_name = project_name or project_id
    init_team(bridge, project_id, team_id, f"{display_name} Error-Learning Team")

    error_agent_id = f"agent-{project_id}-error-analyst"
    init_agent(
        bridge,
        project_id=project_id,
        team_id=team_id,
        agent_id=error_agent_id,
        agent_name=f"{display_name} Error Analyst",
        role="error_analyst",
        personality="Analytical and thorough. Traces errors to root causes. Turns failures into lasting knowledge.",
        evolution_goal="Improve root cause analysis accuracy, error pattern recognition, and knowledge transfer effectiveness",
    )


def init_test_team(bridge: EasybaseBridge, project_id: str, team_id: str, project_name: str = ""):
    """Initialize test team with a test_lead agent."""
    display_name = project_name or project_id
    init_team(bridge, project_id, team_id, f"{display_name} Test Team")

    test_lead_id = f"agent-{project_id}-test-lead"
    init_agent(
        bridge,
        project_id=project_id,
        team_id=team_id,
        agent_id=test_lead_id,
        agent_name=f"{display_name} Test Lead",
        role="test_lead",
        personality="Methodical and coverage-obsessed. Designs tests that catch what others miss. Thinks in edge cases and failure modes.",
        evolution_goal="Improve test plan coverage, edge case detection, and regression prevention",
    )


def init_error_feedback_team(bridge: EasybaseBridge, project_id: str, team_id: str, project_name: str = ""):
    """Initialize error feedback team with an error_feedback_lead agent."""
    display_name = project_name or project_id
    init_team(bridge, project_id, team_id, f"{display_name} Error Feedback Team")

    feedback_lead_id = f"agent-{project_id}-error-feedback-lead"
    init_agent(
        bridge,
        project_id=project_id,
        team_id=team_id,
        agent_id=feedback_lead_id,
        agent_name=f"{display_name} Error Feedback Lead",
        role="error_feedback_lead",
        personality="Vigilant and persistent. Tracks every error to resolution. Identifies recurring patterns and escalates systemic issues.",
        evolution_goal="Improve error pattern recognition, correction ticket quality, and resolution tracking accuracy",
    )


def init_leader_guide(bridge: EasybaseBridge, project_id: str, project_name: str = ""):
    """Initialize leader guide for a department."""
    display_name = project_name or project_id
    guide_content = _load_template("leader_guide.md").replace("{{PROJECT_NAME}}", display_name)

    bridge.store_chunk(
        chunk_id=f"leader-guide-{project_id}",
        summary=f"Leader guide and project structure for {display_name}",
        body=guide_content,
        domain="context",
        tags=f"leader, guide, structure, main idea, {project_id}, decision framework, teams",
        tree_path=f"server/{project_id}",
        stored_by="system",
        stored_by_type="system",
        channel_origin=project_id,
        visibility="project",
    )


def init_vision(bridge: EasybaseBridge, project_id: str, project_name: str = ""):
    """Initialize vision.md for a department."""
    display_name = project_name or project_id
    vision_content = _load_template("vision.md").replace("{{PROJECT_NAME}}", display_name)

    bridge.store_chunk(
        chunk_id=f"vision-{project_id}",
        summary=f"Long-term vision and strategic direction for {display_name}",
        body=vision_content,
        domain="context",
        tags=f"vision, strategy, direction, {project_id}, long-term",
        tree_path=f"server/{project_id}",
        stored_by="system",
        stored_by_type="system",
        channel_origin=project_id,
        visibility="project",
    )


def init_full_hierarchy(bridge: EasybaseBridge, config: dict):
    """Initialize the entire hierarchy from managesim.yaml config."""
    server_name = config.get("server", {}).get("name", "My Agent Server")
    init_server(bridge, server_name)

    for project in config.get("projects", []):
        project_id = project["id"]
        project_name = project.get("name", project_id)
        init_project(bridge, project_id, project_name)

        # Auto-create QA and error-learning teams
        qa_team_id = f"team-{project_id}-qa"
        init_qa_team(bridge, project_id, qa_team_id, project_name)

        error_team_id = f"team-{project_id}-error-learning"
        init_error_learning_team(bridge, project_id, error_team_id, project_name)

        # Auto-create test and error-feedback teams
        test_team_id = f"team-{project_id}-test"
        init_test_team(bridge, project_id, test_team_id, project_name)

        feedback_team_id = f"team-{project_id}-error-feedback"
        init_error_feedback_team(bridge, project_id, feedback_team_id, project_name)

        # Create leader guide and vision.md
        init_leader_guide(bridge, project_id, project_name)
        init_vision(bridge, project_id, project_name)
