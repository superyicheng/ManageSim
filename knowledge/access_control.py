"""Access control — visibility filtering for Easybase chunks.

Visibility levels:
  public   — All projects, all agents (DEFAULT)
  project  — Only agents in the same project
  team     — Only agents in the same team
  agent    — Only the storing agent
  private  — Only the human user (never returned to agents)
"""

from typing import Optional


VISIBILITY_LEVELS = ["public", "project", "team", "agent", "private"]


def filter_by_visibility(
    chunks: list[dict],
    requester_id: str,
    requester_project: str = "",
    requester_team: str = "",
    requester_type: str = "agent",  # agent | user
) -> list[dict]:
    """Filter chunks based on visibility rules.

    Args:
        chunks: List of chunk metadata dicts (with visibility, stored_by, etc.)
        requester_id: ID of the requesting agent/user
        requester_project: Project the requester belongs to
        requester_team: Team the requester belongs to
        requester_type: "agent" or "user"

    Returns:
        Filtered list of chunks the requester can see.
    """
    filtered = []

    for chunk in chunks:
        vis = chunk.get("visibility", "public")

        if vis == "public":
            filtered.append(chunk)

        elif vis == "project":
            chunk_origin = chunk.get("channel_origin", "")
            if requester_project and chunk_origin == requester_project:
                filtered.append(chunk)

        elif vis == "team":
            chunk_tree = chunk.get("tree_path", "")
            if requester_project and requester_team:
                team_prefix = f"server/{requester_project}/{requester_team}"
                if chunk_tree.startswith(team_prefix):
                    filtered.append(chunk)

        elif vis == "agent":
            if chunk.get("stored_by") == requester_id:
                filtered.append(chunk)

        elif vis == "private":
            # Only human users can see private chunks
            if requester_type == "user":
                filtered.append(chunk)

        else:
            # Unknown visibility — treat as public (safe default)
            filtered.append(chunk)

    return filtered


def search_with_access_control(
    bridge,  # EasybaseBridge instance
    query: str,
    requester_id: str,
    requester_project: str = "",
    requester_team: str = "",
    requester_type: str = "agent",
    scope: str = "",
    top_k: int = 10,
) -> list[dict]:
    """Search Easybase with visibility filtering."""
    results = bridge.search(query, scope=scope, top_k=top_k * 3)  # Over-fetch to account for filtering
    filtered = filter_by_visibility(
        results,
        requester_id=requester_id,
        requester_project=requester_project,
        requester_team=requester_team,
        requester_type=requester_type,
    )
    return filtered[:top_k]
