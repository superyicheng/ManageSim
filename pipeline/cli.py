#!/usr/bin/env python3
"""managesim-task CLI — single enforcement point for all task operations.

Inspired by Edict's kanban_update.py. All agents interact with the task system
through this validated CLI tool.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import yaml
from filelock import FileLock

from .state_machine import StateMachine
from .sanitizer import sanitize_title, sanitize_summary
from .permissions import PermissionMatrix
from .progress import ProgressReport, ProgressStep
from .review_gate import ReviewGate, ReviewResult, ReviewVerdict, AxisScore, ReviewAxis
from .error_router import ErrorRouter, ErrorType, ErrorSeverity, ErrorStatus
from .qa_gate import QAGate, QAResult, QAVerdict


TASKS_DIR = os.environ.get("MANAGESIM_TASKS_DIR", "./data/tasks")
CONFIG_DIR = os.environ.get("MANAGESIM_CONFIG_DIR", "./config")


def _ensure_tasks_dir():
    os.makedirs(TASKS_DIR, exist_ok=True)


def _task_path(task_id):
    return os.path.join(TASKS_DIR, f"{task_id}.json")


def _load_task(task_id):
    path = _task_path(task_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _save_task(task_id, data):
    _ensure_tasks_dir()
    path = _task_path(task_id)
    lock_path = path + ".lock"
    with FileLock(lock_path):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


def _next_task_id(project):
    _ensure_tasks_dir()
    existing = [f for f in os.listdir(TASKS_DIR) if f.endswith('.json')]
    prefix = f"{project.upper()}-"
    nums = []
    for f in existing:
        name = f.replace('.json', '')
        if name.startswith(prefix):
            try:
                nums.append(int(name[len(prefix):]))
            except ValueError:
                pass
    next_num = max(nums, default=0) + 1
    return f"{prefix}{next_num:03d}"


def _load_pipeline(pipeline_name):
    path = os.path.join(CONFIG_DIR, "pipelines", f"{pipeline_name}.yaml")
    if os.path.exists(path):
        return StateMachine.from_yaml(path)
    return StateMachine()  # default


@click.group()
def cli():
    """ManageSim Task CLI — single enforcement point for all task operations."""
    pass


@cli.command()
@click.option("--project", required=True, help="Project ID")
@click.option("--title", required=True, help="Task title")
@click.option("--description", default="", help="Task description")
@click.option("--assign-to", default="", help="Agent role to assign to")
@click.option("--pipeline", default="default", help="Pipeline to use")
@click.option("--priority", default="normal", type=click.Choice(["low", "normal", "high", "urgent"]))
def create(project, title, description, assign_to, pipeline, priority):
    """Create a new task."""
    clean_title, err = sanitize_title(title)
    if err:
        click.echo(f"ERROR: {err}", err=True)
        sys.exit(1)

    if description:
        clean_desc, err = sanitize_summary(description)
        if err:
            clean_desc = description[:500]
    else:
        clean_desc = ""

    sm = _load_pipeline(pipeline)
    task_id = _next_task_id(project)

    task = {
        "id": task_id,
        "project": project,
        "title": clean_title,
        "description": clean_desc,
        "state": sm.initial_state,
        "pipeline": pipeline,
        "assigned_to": assign_to,
        "priority": priority,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "progress": [],
        "reviews": [],
        "history": [
            {
                "from_state": None,
                "to_state": sm.initial_state,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "Task created",
            }
        ],
    }
    _save_task(task_id, task)
    click.echo(f"Created: {task_id} — {clean_title}")


@cli.command()
@click.argument("task_id")
@click.argument("target_state")
@click.argument("reason", default="")
@click.option("--agent", default="", help="Agent performing the transition")
def transition(task_id, target_state, reason, agent):
    """Transition a task to a new state."""
    task = _load_task(task_id)
    if not task:
        click.echo(f"ERROR: Task {task_id} not found", err=True)
        sys.exit(1)

    sm = _load_pipeline(task["pipeline"])
    current = task["state"]
    ok, msg = sm.validate_transition(current, target_state)
    if not ok:
        click.echo(f"ERROR: {msg}", err=True)
        sys.exit(1)

    task["state"] = target_state
    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    task["history"].append({
        "from_state": current,
        "to_state": target_state,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason or f"Transitioned by {agent or 'unknown'}",
        "agent": agent,
    })
    _save_task(task_id, task)
    click.echo(f"Transitioned: {task_id} {current} → {target_state}")

    # Cascade cancellation to sub-tasks
    if target_state == "Cancelled" and task.get("sub_tasks"):
        for sub_id in task["sub_tasks"]:
            sub = _load_task(sub_id)
            if sub and sub.get("state") not in ("Done", "Cancelled"):
                sub["state"] = "Cancelled"
                sub["updated_at"] = datetime.now(timezone.utc).isoformat()
                sub["history"].append({
                    "from_state": sub.get("state", "unknown"),
                    "to_state": "Cancelled",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "reason": f"Parent {task_id} cancelled",
                    "agent": agent,
                })
                _save_task(sub_id, sub)
                click.echo(f"  Cascade cancelled: {sub_id}")


@cli.command()
@click.argument("task_id")
@click.argument("text")
@click.argument("checklist", default="")
@click.option("--tokens", default=0, type=int)
@click.option("--cost", default=0.0, type=float)
@click.option("--elapsed", default=0.0, type=float)
@click.option("--agent", default="")
def progress(task_id, text, checklist, tokens, cost, elapsed, agent):
    """Report progress on a task."""
    task = _load_task(task_id)
    if not task:
        click.echo(f"ERROR: Task {task_id} not found", err=True)
        sys.exit(1)

    report = {
        "text": text,
        "checklist": checklist,
        "tokens": tokens,
        "cost": cost,
        "elapsed": elapsed,
        "agent": agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    task["progress"].append(report)
    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_task(task_id, task)
    click.echo(f"Progress recorded for {task_id}")


@cli.command()
@click.argument("task_id")
@click.argument("summary")
@click.option("--artifacts", default="", help="Path to output artifacts")
@click.option("--agent", default="")
@click.option("--check-children", is_flag=True, help="Warn if sub-tasks are not Done")
def done(task_id, summary, artifacts, agent, check_children):
    """Complete a task."""
    task = _load_task(task_id)
    if not task:
        click.echo(f"ERROR: Task {task_id} not found", err=True)
        sys.exit(1)

    # Check sub-task completion if requested
    if check_children and task.get("sub_tasks"):
        incomplete = []
        for sub_id in task["sub_tasks"]:
            sub = _load_task(sub_id)
            if sub and sub.get("state") != "Done":
                incomplete.append(f"  {sub_id} [{sub['state']}] {sub.get('title', '')}")
        if incomplete:
            click.echo(f"WARNING: {len(incomplete)} sub-task(s) not Done:", err=True)
            for line in incomplete:
                click.echo(line, err=True)

    sm = _load_pipeline(task["pipeline"])
    current = task["state"]

    # Find path to Done
    terminal = "Done"
    ok, msg = sm.validate_transition(current, terminal)
    if not ok:
        click.echo(f"ERROR: Cannot complete from state {current}. {msg}", err=True)
        sys.exit(1)

    task["state"] = terminal
    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    task["completion"] = {
        "summary": summary,
        "artifacts": artifacts,
        "agent": agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    task["history"].append({
        "from_state": current,
        "to_state": terminal,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": f"Completed: {summary[:80]}",
        "agent": agent,
    })
    _save_task(task_id, task)
    click.echo(f"Completed: {task_id}")


@cli.command()
@click.argument("parent_task_id")
@click.option("--title", required=True, help="Sub-task title")
@click.option("--summary", required=True, help="Brief: what the worker needs to do")
@click.option("--background", default="", help="Brief: project context (max 2000 chars)")
@click.option("--requirements", default="", help="Brief: acceptance criteria")
@click.option("--constraints", default="", help="Brief: boundaries and limitations")
@click.option("--references", default="", help="Brief: pipe-delimited chunk IDs or paths")
@click.option("--assign-to", default="", help="Worker agent to assign to")
@click.option("--priority", default="normal", type=click.Choice(["low", "normal", "high", "urgent"]))
def delegate(parent_task_id, title, summary, background, requirements, constraints, references, assign_to, priority):
    """Create a sub-task with a complete brief from a parent task.

    The leader uses this to delegate work to workers. Each sub-task includes
    a self-contained brief with all context the worker needs.
    """
    parent = _load_task(parent_task_id)
    if not parent:
        click.echo(f"ERROR: Parent task {parent_task_id} not found", err=True)
        sys.exit(1)

    # Parent must be in an active planning/execution state
    allowed_states = {"Planning", "Review", "Assigned", "Executing"}
    if parent["state"] not in allowed_states:
        click.echo(
            f"ERROR: Cannot delegate from state '{parent['state']}'. "
            f"Allowed: {sorted(allowed_states)}",
            err=True,
        )
        sys.exit(1)

    # Prevent nested delegation (max 1 level deep)
    if parent.get("parent_task"):
        click.echo("ERROR: Cannot delegate from a sub-task. Only top-level tasks can be delegated.", err=True)
        sys.exit(1)

    clean_title, err = sanitize_title(title)
    if err:
        click.echo(f"ERROR: {err}", err=True)
        sys.exit(1)

    # Truncate background to 2000 chars
    if len(background) > 2000:
        background = background[:2000]
        click.echo("WARNING: Background truncated to 2000 characters. Use --references for longer context.", err=True)

    # Build the brief
    ref_list = [r.strip() for r in references.split("|") if r.strip()] if references else []
    brief = {
        "summary": summary,
        "background": background,
        "requirements": requirements,
        "constraints": constraints,
        "references": ref_list,
    }

    # Create the sub-task
    project = parent["project"]
    pipeline = parent.get("pipeline", "default")
    sub_task_id = _next_task_id(project)

    sub_task = {
        "id": sub_task_id,
        "project": project,
        "title": clean_title,
        "description": summary,
        "state": "Assigned",
        "pipeline": pipeline,
        "assigned_to": assign_to,
        "priority": priority,
        "parent_task": parent_task_id,
        "brief": brief,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "progress": [],
        "reviews": [],
        "history": [
            {
                "from_state": None,
                "to_state": "Assigned",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": f"Delegated from {parent_task_id} by leader",
            }
        ],
    }
    _save_task(sub_task_id, sub_task)

    # Update parent with sub-task link
    if "sub_tasks" not in parent:
        parent["sub_tasks"] = []
    parent["sub_tasks"].append(sub_task_id)
    parent["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_task(parent_task_id, parent)

    click.echo(f"Delegated: {sub_task_id} (from {parent_task_id}) — {clean_title}")
    click.echo(f"  Brief: {summary[:80]}")
    if assign_to:
        click.echo(f"  Assigned to: {assign_to}")


@cli.command()
@click.argument("task_id")
def show(task_id):
    """Show task details."""
    task = _load_task(task_id)
    if not task:
        click.echo(f"ERROR: Task {task_id} not found", err=True)
        sys.exit(1)
    click.echo(json.dumps(task, indent=2))


@cli.command("list")
@click.option("--project", default=None, help="Filter by project")
@click.option("--state", default=None, help="Filter by state")
def list_tasks(project, state):
    """List all tasks."""
    _ensure_tasks_dir()
    tasks = []
    for f in sorted(os.listdir(TASKS_DIR)):
        if not f.endswith('.json'):
            continue
        with open(os.path.join(TASKS_DIR, f)) as fh:
            task = json.load(fh)
        if project and task.get("project") != project:
            continue
        if state and task.get("state") != state:
            continue
        tasks.append(task)

    for t in tasks:
        priority_mark = "!" if t.get("priority") == "urgent" else " "
        click.echo(f"{priority_mark} {t['id']:>12} [{t['state']:>10}] {t['title']}")

    if not tasks:
        click.echo("No tasks found.")


@cli.command("qa-report")
@click.argument("task_id")
@click.argument("verdict", type=click.Choice(["pass", "fail", "conditional"]))
@click.option("--defects", default="", help="Pipe-delimited defect descriptions")
@click.option("--test-coverage", default="", help="Test coverage summary")
@click.option("--structural-notes", default="", help="Notes on structural fit")
@click.option("--agent", default="", help="QA tester agent ID")
def qa_report(task_id, verdict, defects, test_coverage, structural_notes, agent):
    """Submit QA test results for a task."""
    task = _load_task(task_id)
    if not task:
        click.echo(f"ERROR: Task {task_id} not found", err=True)
        sys.exit(1)

    if task["state"] != "QA":
        click.echo(f"ERROR: Task {task_id} is in state '{task['state']}', not 'QA'", err=True)
        sys.exit(1)

    defect_list = [d.strip() for d in defects.split("|") if d.strip()] if defects else []

    qa_result = {
        "verdict": verdict,
        "defects": defect_list,
        "test_coverage": test_coverage,
        "structural_notes": structural_notes,
        "tester_agent": agent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if "qa_results" not in task:
        task["qa_results"] = []
    task["qa_results"].append(qa_result)
    task["updated_at"] = datetime.now(timezone.utc).isoformat()

    # If failed, transition back to Executing
    if verdict == "fail":
        sm = _load_pipeline(task["pipeline"])
        ok, msg = sm.validate_transition("QA", "Executing")
        if ok:
            task["state"] = "Executing"
            task["history"].append({
                "from_state": "QA",
                "to_state": "Executing",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": f"QA failed: {'; '.join(defect_list[:3]) if defect_list else 'defects found'}",
                "agent": agent,
            })

    _save_task(task_id, task)
    click.echo(f"QA {verdict}: {task_id} ({len(defect_list)} defects)")


@cli.command("error-report")
@click.argument("task_id")
@click.option("--error-type", required=True, type=click.Choice(["decision", "execution", "review", "integration"]))
@click.option("--responsible-agent", required=True, help="Agent responsible for the error")
@click.option("--responsible-role", required=True, help="Role of the responsible agent")
@click.option("--description", default="", help="Error description")
@click.option("--severity", default="medium", type=click.Choice(["low", "medium", "high", "critical"]))
@click.option("--project", default="", help="Project ID (defaults to task's project)")
def error_report(task_id, error_type, responsible_agent, responsible_role, description, severity, project):
    """Create an error report for a task."""
    task = _load_task(task_id)
    if not task:
        click.echo(f"ERROR: Task {task_id} not found", err=True)
        sys.exit(1)

    project_id = project or task.get("project", "unknown")

    report = {
        "id": f"ERR-{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "task_id": task_id,
        "project_id": project_id,
        "error_type": error_type,
        "responsible_agent": responsible_agent,
        "responsible_role": responsible_role,
        "description": description,
        "severity": severity,
        "root_cause": "",
        "lesson_learned": "",
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
    }

    # Store error report on the task
    if "error_reports" not in task:
        task["error_reports"] = []
    task["error_reports"].append(report)
    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_task(task_id, task)

    # Also save as standalone error report file
    _ensure_tasks_dir()
    error_path = os.path.join(TASKS_DIR, f"{report['id']}.error.json")
    with open(error_path, 'w') as f:
        json.dump(report, f, indent=2)

    # Determine routing targets
    routing = {
        "decision": ["leader"],
        "execution": ["worker"],
        "review": ["reviewer"],
        "integration": ["leader", "worker"],
    }
    targets = routing.get(error_type, ["leader"])

    click.echo(f"Error report created: {report['id']} → routes to: {', '.join(targets)}")


@cli.command("error-learn")
@click.argument("error_id")
@click.argument("root_cause")
@click.argument("lesson")
@click.option("--agent", default="", help="Agent submitting the lesson")
def error_learn(error_id, root_cause, lesson, agent):
    """Record a root cause analysis and lesson learned for an error."""
    # Find the error report file
    _ensure_tasks_dir()
    error_path = os.path.join(TASKS_DIR, f"{error_id}.error.json")

    if not os.path.exists(error_path):
        click.echo(f"ERROR: Error report {error_id} not found", err=True)
        sys.exit(1)

    with open(error_path) as f:
        report = json.load(f)

    report["root_cause"] = root_cause
    report["lesson_learned"] = lesson
    report["status"] = "resolved"
    report["resolved_at"] = datetime.now(timezone.utc).isoformat()
    report["resolved_by"] = agent

    with open(error_path, 'w') as f:
        json.dump(report, f, indent=2)

    # Also update the error on the task if it exists
    task = _load_task(report.get("task_id", ""))
    if task and "error_reports" in task:
        for err in task["error_reports"]:
            if err.get("id") == error_id:
                err["root_cause"] = root_cause
                err["lesson_learned"] = lesson
                err["status"] = "resolved"
                err["resolved_at"] = report["resolved_at"]
                break
        _save_task(report["task_id"], task)

    click.echo(f"Error resolved: {error_id}")
    click.echo(f"  Root cause: {root_cause[:80]}")
    click.echo(f"  Lesson: {lesson[:80]}")


def main():
    cli()


if __name__ == "__main__":
    main()
