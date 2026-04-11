"""Unified MCP server bridge for ManageSim tool integrations.

Exposes ManageSim operations as MCP tools that agents can call.
Follows the same FastMCP pattern as Easybase's mcp_server.py.
"""

import os
import json
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.cli import _load_task, _save_task, _next_task_id, _load_pipeline
from pipeline.sanitizer import sanitize_title, sanitize_summary
from pipeline.state_machine import StateMachine


def task_create(project: str, title: str, description: str = "", pipeline: str = "default") -> str:
    """Create a new task via the pipeline."""
    clean_title, err = sanitize_title(title)
    if err:
        return json.dumps({"error": err})

    from datetime import datetime
    sm = _load_pipeline(pipeline)
    task_id = _next_task_id(project)

    task = {
        "id": task_id,
        "project": project,
        "title": clean_title,
        "description": description[:500] if description else "",
        "state": sm.initial_state,
        "pipeline": pipeline,
        "assigned_to": "",
        "priority": "normal",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "progress": [],
        "reviews": [],
        "history": [],
    }
    _save_task(task_id, task)
    return json.dumps({"status": "created", "task_id": task_id, "title": clean_title})


def task_transition(task_id: str, target_state: str, reason: str = "") -> str:
    """Transition a task to a new state (validated)."""
    task = _load_task(task_id)
    if not task:
        return json.dumps({"error": f"Task {task_id} not found"})

    sm = _load_pipeline(task.get("pipeline", "default"))
    current = task["state"]
    ok, msg = sm.validate_transition(current, target_state)
    if not ok:
        return json.dumps({"error": msg})

    from datetime import datetime
    task["state"] = target_state
    task["updated_at"] = datetime.utcnow().isoformat()
    _save_task(task_id, task)
    return json.dumps({"status": "transitioned", "from": current, "to": target_state})


def task_progress(task_id: str, text: str, checklist: str = "") -> str:
    """Report progress on a task."""
    task = _load_task(task_id)
    if not task:
        return json.dumps({"error": f"Task {task_id} not found"})

    from datetime import datetime
    report = {
        "text": text,
        "checklist": checklist,
        "timestamp": datetime.utcnow().isoformat(),
    }
    task.setdefault("progress", []).append(report)
    task["updated_at"] = datetime.utcnow().isoformat()
    _save_task(task_id, task)
    return json.dumps({"status": "recorded", "task_id": task_id})


def task_show(task_id: str) -> str:
    """Show task details."""
    task = _load_task(task_id)
    if not task:
        return json.dumps({"error": f"Task {task_id} not found"})
    return json.dumps(task, indent=2)


def task_delegate(
    parent_task_id: str,
    title: str,
    summary: str,
    background: str = "",
    requirements: str = "",
    constraints: str = "",
    references: str = "",
    assign_to: str = "",
) -> str:
    """Create a sub-task with a complete brief from a parent task.

    The leader uses this to delegate work to workers. Each sub-task includes
    a self-contained brief with all context the worker needs.
    """
    parent = _load_task(parent_task_id)
    if not parent:
        return json.dumps({"error": f"Parent task {parent_task_id} not found"})

    allowed_states = {"Planning", "Review", "Assigned", "Executing"}
    if parent["state"] not in allowed_states:
        return json.dumps({"error": f"Cannot delegate from state '{parent['state']}'"})

    if parent.get("parent_task"):
        return json.dumps({"error": "Cannot delegate from a sub-task"})

    clean_title, err = sanitize_title(title)
    if err:
        return json.dumps({"error": err})

    if len(background) > 2000:
        background = background[:2000]

    ref_list = [r.strip() for r in references.split("|") if r.strip()] if references else []
    brief = {
        "summary": summary,
        "background": background,
        "requirements": requirements,
        "constraints": constraints,
        "references": ref_list,
    }

    project = parent["project"]
    pipeline = parent.get("pipeline", "default")
    sub_task_id = _next_task_id(project)

    from datetime import datetime
    sub_task = {
        "id": sub_task_id,
        "project": project,
        "title": clean_title,
        "description": summary,
        "state": "Assigned",
        "pipeline": pipeline,
        "assigned_to": assign_to,
        "priority": parent.get("priority", "normal"),
        "parent_task": parent_task_id,
        "brief": brief,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "progress": [],
        "reviews": [],
        "history": [
            {
                "from_state": None,
                "to_state": "Assigned",
                "timestamp": datetime.utcnow().isoformat(),
                "reason": f"Delegated from {parent_task_id} by leader",
            }
        ],
    }
    _save_task(sub_task_id, sub_task)

    if "sub_tasks" not in parent:
        parent["sub_tasks"] = []
    parent["sub_tasks"].append(sub_task_id)
    parent["updated_at"] = datetime.utcnow().isoformat()
    _save_task(parent_task_id, parent)

    return json.dumps({
        "status": "delegated",
        "sub_task_id": sub_task_id,
        "parent_task_id": parent_task_id,
        "title": clean_title,
        "assigned_to": assign_to,
    })


# MCP server setup (if fastmcp available)
def create_mcp_server():
    """Create MCP server exposing ManageSim tools."""
    try:
        from fastmcp import FastMCP
    except ImportError:
        print("fastmcp not installed. MCP bridge unavailable.")
        return None

    mcp = FastMCP("ManageSim Tools")

    @mcp.tool()
    def managesim_task_create(project: str, title: str, description: str = "", pipeline: str = "default") -> str:
        """Create a new task in ManageSim."""
        return task_create(project, title, description, pipeline)

    @mcp.tool()
    def managesim_task_transition(task_id: str, target_state: str, reason: str = "") -> str:
        """Transition a task to a new state (validated against pipeline)."""
        return task_transition(task_id, target_state, reason)

    @mcp.tool()
    def managesim_task_progress(task_id: str, text: str, checklist: str = "") -> str:
        """Report progress on a task."""
        return task_progress(task_id, text, checklist)

    @mcp.tool()
    def managesim_task_show(task_id: str) -> str:
        """Show task details."""
        return task_show(task_id)

    @mcp.tool()
    def managesim_task_delegate(
        parent_task_id: str,
        title: str,
        summary: str,
        background: str = "",
        requirements: str = "",
        constraints: str = "",
        references: str = "",
        assign_to: str = "",
    ) -> str:
        """Delegate a sub-task from a parent task with a complete brief for the worker."""
        return task_delegate(parent_task_id, title, summary, background, requirements, constraints, references, assign_to)

    return mcp


if __name__ == "__main__":
    server = create_mcp_server()
    if server:
        server.run()
    else:
        print("MCP server could not be created. Check fastmcp installation.")
