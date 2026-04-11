"""Asset Base — FastAPI REST API server.

Comprehensive knowledge hub managing tasks, skills, agents, teams,
context, decisions, statistics, and provenance.
"""

import os
import yaml
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from typing import Optional

from .db import Database
from .hierarchy import HierarchyManager
from .provenance import ProvenanceTracker

app = FastAPI(title="ManageSim Asset Base", version="1.0.0")

# Initialize on startup
db = None
hierarchy = None
provenance = None


@app.on_event("startup")
def startup():
    global db, hierarchy, provenance
    db_path = os.environ.get("ASSET_BASE_DB", "./data/asset_base.db")
    db = Database(db_path)
    hierarchy = HierarchyManager(db)
    provenance = ProvenanceTracker(db)


# --- Context ---
@app.get("/api/context/{level}")
def get_context(level: str, id: str = ""):
    return hierarchy.get_context(level, id)


# --- Tasks ---
@app.post("/api/tasks")
def create_task(task: dict):
    task.setdefault("created_at", datetime.utcnow().isoformat())
    db.create_task(task)
    return {"status": "created", "id": task["id"]}

@app.get("/api/tasks")
def list_tasks(
    project: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    return db.list_tasks(project_id=project, state=state, limit=limit, offset=offset)

@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task

@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, updates: dict):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    db.update_task(task_id, updates)
    return {"status": "updated", "id": task_id}

@app.get("/api/tasks/{task_id}/sub-tasks")
def get_sub_tasks(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return db.get_sub_tasks(task_id)


# --- Skills ---
@app.get("/api/skills")
def list_skills(
    level: Optional[str] = None,
    id: Optional[str] = None,
):
    return db.list_skills(level=level, level_id=id)

@app.post("/api/skills")
def create_skill(skill: dict):
    db.create_skill(skill)
    return {"status": "created", "id": skill["id"]}

@app.patch("/api/skills/{skill_id}/proficiency")
def update_proficiency(skill_id: str, proficiency: float):
    db.update_skill_proficiency(skill_id, proficiency)
    return {"status": "updated"}


# --- Agents ---
@app.get("/api/agents")
def list_agents(
    project: Optional[str] = None,
    team: Optional[str] = None,
):
    return db.list_agents(project_id=project, team_id=team)

@app.get("/api/agents/{agent_id}")
def get_agent(agent_id: str):
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent

@app.post("/api/agents")
def create_agent(agent: dict):
    agent.setdefault("created_at", datetime.utcnow().isoformat())
    db.create_agent(agent)
    return {"status": "created", "id": agent["id"]}

@app.get("/api/agents/{agent_id}/performance")
def agent_performance(agent_id: str):
    perf = db.get_agent_performance(agent_id)
    if not perf:
        raise HTTPException(404, "Agent not found")
    return perf


# --- QA Results ---
@app.post("/api/qa-results")
def create_qa_result(result: dict):
    result.setdefault("created_at", datetime.utcnow().isoformat())
    result.setdefault("id", f"QA-{result.get('task_id', 'unknown')}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    db.create_qa_result(result)
    return {"status": "created", "id": result["id"]}

@app.get("/api/qa-results")
def list_qa_results(
    task: Optional[str] = None,
    project: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    return db.list_qa_results(task_id=task, project_id=project, limit=limit)


# --- Error Reports ---
@app.post("/api/error-reports")
def create_error_report(report: dict):
    report.setdefault("created_at", datetime.utcnow().isoformat())
    report.setdefault("status", "open")
    db.create_error_report(report)
    return {"status": "created", "id": report["id"]}

@app.get("/api/error-reports")
def list_error_reports(
    agent: Optional[str] = None,
    project: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    return db.list_error_reports(agent=agent, project_id=project, status=status, limit=limit)

@app.patch("/api/error-reports/{report_id}")
def update_error_report(report_id: str, updates: dict):
    existing = db.get_error_report(report_id)
    if not existing:
        raise HTTPException(404, "Error report not found")
    db.update_error_report(report_id, updates)
    return {"status": "updated"}

@app.get("/api/error-reports/{report_id}/lesson")
def get_error_lesson(report_id: str):
    report = db.get_error_report(report_id)
    if not report:
        raise HTTPException(404, "Error report not found")
    return {
        "id": report_id,
        "root_cause": report.get("root_cause", ""),
        "lesson_learned": report.get("lesson_learned", ""),
        "status": report.get("status", ""),
    }


# --- Statistics ---
@app.get("/api/stats/server")
def server_stats():
    return hierarchy.get_context("server")

@app.get("/api/stats/project/{project_id}")
def project_stats(project_id: str):
    return hierarchy.get_context("project", project_id)

@app.get("/api/stats/costs")
def cost_stats(period: str = "monthly"):
    return {"period": period, "data": db.get_stat(f"costs_{period}") or {}}


# --- Provenance ---
@app.get("/api/provenance")
def query_provenance(
    stored_by: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    return db.query_provenance(stored_by=stored_by, channel_origin=channel, limit=limit)


def main():
    import uvicorn
    port = int(os.environ.get("ASSET_BASE_PORT", "8100"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
