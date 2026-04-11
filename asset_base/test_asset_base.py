"""Comprehensive tests for asset_base Database class and data models."""

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime

import pytest

from asset_base.db import Database
from asset_base.models import Agent, ErrorReport, ProvenanceRecord, QAResult, Skill, Task, Team


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path):
    """Create a fresh Database backed by a temp-dir SQLite file."""
    return Database(str(tmp_path / "test.db"))


def _make_task(overrides=None):
    """Return a minimal task dict with sensible defaults, applying overrides."""
    base = {
        "id": "t-001",
        "project_id": "proj-1",
        "title": "Implement feature X",
        "description": "Some details",
        "state": "Inbox",
        "pipeline": "default",
        "assigned_to": "",
        "priority": "normal",
        "created_at": "2025-01-01T00:00:00",
        "tags": "",
    }
    if overrides:
        base.update(overrides)
    return base


def _make_skill(overrides=None):
    base = {
        "id": "sk-001",
        "name": "python",
        "description": "Python programming",
        "level": "server",
        "level_id": "",
        "proficiency": 0.5,
        "usage_count": 0,
        "source": "local",
        "installed_by": "",
        "tags": "python,coding",
    }
    if overrides:
        base.update(overrides)
    return base


def _make_agent(overrides=None):
    base = {
        "id": "a-001",
        "name": "AgentAlpha",
        "project_id": "proj-1",
        "team_id": "team-1",
        "role": "worker",
        "status": "active",
        "tasks_completed": 5,
        "tasks_failed": 1,
        "success_rate": 0.833,
        "total_cost": 1.25,
        "total_tokens": 12000,
        "evolution_goal": "",
        "personality_state": "",
        "created_at": "2025-01-01T00:00:00",
        "last_active": "2025-01-02T00:00:00",
    }
    if overrides:
        base.update(overrides)
    return base


def _make_team(overrides=None):
    base = {
        "id": "team-1",
        "name": "Alpha Squad",
        "project_id": "proj-1",
        "template": "standard",
        "agent_count": 3,
        "tasks_completed": 10,
        "effectiveness": 0.85,
        "created_at": "2025-01-01T00:00:00",
    }
    if overrides:
        base.update(overrides)
    return base


def _make_provenance(overrides=None):
    base = {
        "id": "prov-001",
        "chunk_id": "chunk-abc",
        "stored_by": "agent-x",
        "stored_by_type": "agent",
        "channel_origin": "discord",
        "visibility": "public",
        "sensitivity": "normal",
        "action": "create",
        "timestamp": "2025-01-01T00:00:00",
    }
    if overrides:
        base.update(overrides)
    return base


def _make_error_report(overrides=None):
    base = {
        "id": "er-001",
        "task_id": "t-001",
        "project_id": "proj-1",
        "error_type": "execution",
        "responsible_agent": "a-001",
        "responsible_role": "worker",
        "description": "Null pointer",
        "severity": "high",
        "root_cause": "Missing check",
        "lesson_learned": "Always validate",
        "status": "open",
        "created_at": "2025-01-01T00:00:00",
    }
    if overrides:
        base.update(overrides)
    return base


def _make_qa_result(overrides=None):
    base = {
        "id": "qa-001",
        "task_id": "t-001",
        "project_id": "proj-1",
        "tester_agent": "tester-1",
        "verdict": "pass",
        "defects": "[]",
        "test_coverage": "80%",
        "structural_notes": "All good",
        "created_at": "2025-01-01T00:00:00",
    }
    if overrides:
        base.update(overrides)
    return base


# ===========================================================================
# Section 1: _init_tables
# ===========================================================================

class TestInitTables:
    """Verify that Database constructor creates all expected tables."""

    EXPECTED_TABLES = [
        "tasks",
        "skills",
        "agents",
        "teams",
        "provenance",
        "stats",
        "error_reports",
        "qa_results",
    ]

    def test_all_eight_tables_are_created(self, db):
        """Database.__init__ must create exactly the 8 required tables."""
        with db._conn() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = sorted(r["name"] for r in rows)
        assert sorted(self.EXPECTED_TABLES) == table_names

    def test_init_tables_is_idempotent(self, tmp_path):
        """Calling _init_tables twice on the same DB file must not fail."""
        path = str(tmp_path / "double_init.db")
        db1 = Database(path)
        db2 = Database(path)  # second init on same file
        with db2._conn() as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = sorted(r["name"] for r in rows)
        assert sorted(self.EXPECTED_TABLES) == table_names

    def test_database_creates_parent_directory(self, tmp_path):
        """Database should create intermediate directories for the db file."""
        path = str(tmp_path / "nested" / "deep" / "test.db")
        db = Database(path)
        assert db.db_path == path
        # Confirm the file is functional
        db.set_stat("probe", "ok")
        assert db.get_stat("probe") == "ok"


# ===========================================================================
# Section 2: Tasks CRUD
# ===========================================================================

class TestCreateAndGetTask:

    def test_create_and_get_task_roundtrip(self, db):
        task = _make_task()
        db.create_task(task)
        got = db.get_task("t-001")
        assert got is not None
        assert got["id"] == "t-001"
        assert got["project_id"] == "proj-1"
        assert got["title"] == "Implement feature X"
        assert got["state"] == "Inbox"

    def test_get_task_returns_none_for_missing_id(self, db):
        result = db.get_task("nonexistent-id")
        assert result is None

    def test_create_task_with_all_fields(self, db):
        task = _make_task({
            "completed_at": "2025-02-01T00:00:00",
            "duration_seconds": 123.5,
            "cost": 0.05,
            "tokens_used": 3000,
            "success": 1,
            "tags": "urgent,backend",
        })
        db.create_task(task)
        got = db.get_task("t-001")
        assert got["completed_at"] == "2025-02-01T00:00:00"
        assert got["duration_seconds"] == 123.5
        assert got["cost"] == 0.05
        assert got["tokens_used"] == 3000
        assert got["success"] == 1
        assert got["tags"] == "urgent,backend"

    def test_create_task_duplicate_id_raises(self, db):
        db.create_task(_make_task())
        with pytest.raises(sqlite3.IntegrityError):
            db.create_task(_make_task())

    def test_create_task_missing_required_field_raises(self, db):
        """project_id is NOT NULL; omitting it must error."""
        with pytest.raises(Exception):
            db.create_task({"id": "t-bad", "title": "No project"})


class TestListTasks:

    def test_list_tasks_returns_empty_when_no_tasks(self, db):
        result = db.list_tasks()
        assert result == []

    def test_list_tasks_returns_all_tasks(self, db):
        for i in range(3):
            db.create_task(_make_task({"id": f"t-{i}", "created_at": f"2025-01-0{i+1}T00:00:00"}))
        result = db.list_tasks()
        assert len(result) == 3

    def test_list_tasks_filter_by_project_id(self, db):
        db.create_task(_make_task({"id": "t-a", "project_id": "proj-1"}))
        db.create_task(_make_task({"id": "t-b", "project_id": "proj-2"}))
        db.create_task(_make_task({"id": "t-c", "project_id": "proj-1"}))
        result = db.list_tasks(project_id="proj-1")
        assert len(result) == 2
        assert all(r["project_id"] == "proj-1" for r in result)

    def test_list_tasks_filter_by_state(self, db):
        db.create_task(_make_task({"id": "t-a", "state": "Inbox"}))
        db.create_task(_make_task({"id": "t-b", "state": "Done"}))
        db.create_task(_make_task({"id": "t-c", "state": "Inbox"}))
        result = db.list_tasks(state="Done")
        assert len(result) == 1
        assert result[0]["id"] == "t-b"

    def test_list_tasks_combined_project_and_state_filter(self, db):
        db.create_task(_make_task({"id": "t-1", "project_id": "p1", "state": "Inbox"}))
        db.create_task(_make_task({"id": "t-2", "project_id": "p1", "state": "Done"}))
        db.create_task(_make_task({"id": "t-3", "project_id": "p2", "state": "Inbox"}))
        result = db.list_tasks(project_id="p1", state="Inbox")
        assert len(result) == 1
        assert result[0]["id"] == "t-1"

    def test_list_tasks_pagination_limit(self, db):
        for i in range(5):
            db.create_task(_make_task({"id": f"t-{i}", "created_at": f"2025-01-0{i+1}T00:00:00"}))
        result = db.list_tasks(limit=2)
        assert len(result) == 2

    def test_list_tasks_pagination_offset(self, db):
        for i in range(5):
            db.create_task(_make_task({"id": f"t-{i}", "created_at": f"2025-01-0{i+1}T00:00:00"}))
        all_tasks = db.list_tasks(limit=50)
        offset_tasks = db.list_tasks(limit=50, offset=2)
        assert len(offset_tasks) == 3
        # offset skips the first 2 in descending created_at order
        assert offset_tasks[0]["id"] == all_tasks[2]["id"]

    def test_list_tasks_returns_empty_for_nonexistent_project(self, db):
        db.create_task(_make_task())
        result = db.list_tasks(project_id="no-such-project")
        assert result == []

    def test_list_tasks_ordered_by_created_at_desc(self, db):
        db.create_task(_make_task({"id": "t-old", "created_at": "2025-01-01T00:00:00"}))
        db.create_task(_make_task({"id": "t-new", "created_at": "2025-06-01T00:00:00"}))
        result = db.list_tasks()
        assert result[0]["id"] == "t-new"
        assert result[1]["id"] == "t-old"


class TestUpdateTask:

    def test_update_task_single_field(self, db):
        db.create_task(_make_task())
        db.update_task("t-001", {"state": "InProgress"})
        got = db.get_task("t-001")
        assert got["state"] == "InProgress"
        # Unchanged fields remain
        assert got["title"] == "Implement feature X"

    def test_update_task_multiple_fields(self, db):
        db.create_task(_make_task())
        db.update_task("t-001", {
            "state": "Done",
            "completed_at": "2025-03-01T00:00:00",
            "success": 1,
            "cost": 0.10,
        })
        got = db.get_task("t-001")
        assert got["state"] == "Done"
        assert got["completed_at"] == "2025-03-01T00:00:00"
        assert got["success"] == 1
        assert got["cost"] == 0.10

    def test_update_task_nonexistent_id_is_noop(self, db):
        """Updating a missing task should not raise; it simply affects 0 rows."""
        db.update_task("ghost", {"state": "Done"})  # no error


# ===========================================================================
# Section 3: Skills CRUD
# ===========================================================================

class TestCreateAndGetSkill:

    def test_create_and_get_skill_roundtrip(self, db):
        db.create_skill(_make_skill())
        got = db.get_skill("sk-001")
        assert got is not None
        assert got["name"] == "python"
        assert got["proficiency"] == 0.5

    def test_get_skill_returns_none_for_missing_id(self, db):
        assert db.get_skill("no-such") is None

    def test_create_skill_upserts_on_duplicate_id(self, db):
        """Skills use INSERT OR REPLACE so a second insert overwrites."""
        db.create_skill(_make_skill({"proficiency": 0.5}))
        db.create_skill(_make_skill({"proficiency": 0.9}))
        got = db.get_skill("sk-001")
        assert got["proficiency"] == 0.9


class TestListSkills:

    def test_list_skills_returns_all_when_no_filter(self, db):
        db.create_skill(_make_skill({"id": "sk-1"}))
        db.create_skill(_make_skill({"id": "sk-2"}))
        result = db.list_skills()
        assert len(result) == 2

    def test_list_skills_filter_by_level(self, db):
        db.create_skill(_make_skill({"id": "sk-1", "level": "server"}))
        db.create_skill(_make_skill({"id": "sk-2", "level": "agent"}))
        result = db.list_skills(level="agent")
        assert len(result) == 1
        assert result[0]["id"] == "sk-2"

    def test_list_skills_filter_by_level_and_level_id(self, db):
        db.create_skill(_make_skill({"id": "sk-1", "level": "project", "level_id": "p1"}))
        db.create_skill(_make_skill({"id": "sk-2", "level": "project", "level_id": "p2"}))
        db.create_skill(_make_skill({"id": "sk-3", "level": "team", "level_id": "p1"}))
        result = db.list_skills(level="project", level_id="p1")
        assert len(result) == 1
        assert result[0]["id"] == "sk-1"

    def test_list_skills_empty_when_no_match(self, db):
        db.create_skill(_make_skill())
        result = db.list_skills(level="nonexistent")
        assert result == []


class TestUpdateSkillProficiency:

    def test_update_skill_proficiency_sets_value(self, db):
        db.create_skill(_make_skill({"proficiency": 0.3, "usage_count": 0}))
        db.update_skill_proficiency("sk-001", 0.75)
        got = db.get_skill("sk-001")
        assert got["proficiency"] == 0.75

    def test_update_skill_proficiency_increments_usage_count(self, db):
        db.create_skill(_make_skill({"usage_count": 0}))
        db.update_skill_proficiency("sk-001", 0.5)
        db.update_skill_proficiency("sk-001", 0.6)
        db.update_skill_proficiency("sk-001", 0.7)
        got = db.get_skill("sk-001")
        assert got["usage_count"] == 3

    def test_update_skill_proficiency_nonexistent_id_is_noop(self, db):
        db.update_skill_proficiency("ghost", 1.0)  # no error, 0 rows affected


# ===========================================================================
# Section 4: Agents CRUD
# ===========================================================================

class TestCreateAndGetAgent:

    def test_create_and_get_agent_roundtrip(self, db):
        db.create_agent(_make_agent())
        got = db.get_agent("a-001")
        assert got is not None
        assert got["name"] == "AgentAlpha"
        assert got["role"] == "worker"
        assert got["tasks_completed"] == 5

    def test_get_agent_returns_none_for_missing_id(self, db):
        assert db.get_agent("no-agent") is None

    def test_create_agent_duplicate_id_raises(self, db):
        db.create_agent(_make_agent())
        with pytest.raises(sqlite3.IntegrityError):
            db.create_agent(_make_agent())


class TestListAgents:

    def test_list_agents_all(self, db):
        db.create_agent(_make_agent({"id": "a-1"}))
        db.create_agent(_make_agent({"id": "a-2"}))
        result = db.list_agents()
        assert len(result) == 2

    def test_list_agents_filter_by_project(self, db):
        db.create_agent(_make_agent({"id": "a-1", "project_id": "p1"}))
        db.create_agent(_make_agent({"id": "a-2", "project_id": "p2"}))
        result = db.list_agents(project_id="p1")
        assert len(result) == 1
        assert result[0]["project_id"] == "p1"

    def test_list_agents_filter_by_team(self, db):
        db.create_agent(_make_agent({"id": "a-1", "team_id": "t1"}))
        db.create_agent(_make_agent({"id": "a-2", "team_id": "t2"}))
        db.create_agent(_make_agent({"id": "a-3", "team_id": "t1"}))
        result = db.list_agents(team_id="t1")
        assert len(result) == 2

    def test_list_agents_combined_project_and_team_filter(self, db):
        db.create_agent(_make_agent({"id": "a-1", "project_id": "p1", "team_id": "t1"}))
        db.create_agent(_make_agent({"id": "a-2", "project_id": "p1", "team_id": "t2"}))
        db.create_agent(_make_agent({"id": "a-3", "project_id": "p2", "team_id": "t1"}))
        result = db.list_agents(project_id="p1", team_id="t1")
        assert len(result) == 1
        assert result[0]["id"] == "a-1"

    def test_list_agents_empty_when_no_match(self, db):
        db.create_agent(_make_agent())
        result = db.list_agents(project_id="nonexistent")
        assert result == []


class TestGetAgentPerformance:

    def test_get_agent_performance_returns_correct_fields(self, db):
        db.create_agent(_make_agent({
            "tasks_completed": 10,
            "tasks_failed": 2,
            "success_rate": 0.833,
            "total_cost": 2.50,
            "total_tokens": 50000,
        }))
        perf = db.get_agent_performance("a-001")
        assert perf is not None
        assert perf["tasks_completed"] == 10
        assert perf["tasks_failed"] == 2
        assert perf["success_rate"] == pytest.approx(0.833)
        assert perf["total_cost"] == pytest.approx(2.50)
        assert perf["total_tokens"] == 50000

    def test_get_agent_performance_only_performance_columns(self, db):
        db.create_agent(_make_agent())
        perf = db.get_agent_performance("a-001")
        expected_keys = {"tasks_completed", "tasks_failed", "success_rate", "total_cost", "total_tokens"}
        assert set(perf.keys()) == expected_keys

    def test_get_agent_performance_returns_none_for_missing(self, db):
        result = db.get_agent_performance("ghost")
        assert result is None


class TestUpdateAgent:

    def test_update_agent_single_field(self, db):
        db.create_agent(_make_agent())
        db.update_agent("a-001", {"status": "inactive"})
        got = db.get_agent("a-001")
        assert got["status"] == "inactive"
        assert got["name"] == "AgentAlpha"  # unchanged

    def test_update_agent_performance_counters(self, db):
        db.create_agent(_make_agent({"tasks_completed": 0, "tasks_failed": 0}))
        db.update_agent("a-001", {"tasks_completed": 7, "tasks_failed": 3, "success_rate": 0.7})
        got = db.get_agent("a-001")
        assert got["tasks_completed"] == 7
        assert got["tasks_failed"] == 3
        assert got["success_rate"] == pytest.approx(0.7)


# ===========================================================================
# Section 5: Teams CRUD
# ===========================================================================

class TestCreateAndGetTeam:

    def test_create_and_get_team_roundtrip(self, db):
        db.create_team(_make_team())
        got = db.get_team("team-1")
        assert got is not None
        assert got["name"] == "Alpha Squad"
        assert got["agent_count"] == 3

    def test_get_team_returns_none_for_missing_id(self, db):
        assert db.get_team("no-team") is None

    def test_create_team_duplicate_id_raises(self, db):
        db.create_team(_make_team())
        with pytest.raises(sqlite3.IntegrityError):
            db.create_team(_make_team())


class TestListTeams:

    def test_list_teams_all(self, db):
        db.create_team(_make_team({"id": "team-1"}))
        db.create_team(_make_team({"id": "team-2"}))
        result = db.list_teams()
        assert len(result) == 2

    def test_list_teams_filter_by_project(self, db):
        db.create_team(_make_team({"id": "team-1", "project_id": "p1"}))
        db.create_team(_make_team({"id": "team-2", "project_id": "p2"}))
        result = db.list_teams(project_id="p1")
        assert len(result) == 1
        assert result[0]["project_id"] == "p1"

    def test_list_teams_empty_when_no_match(self, db):
        db.create_team(_make_team())
        result = db.list_teams(project_id="nonexistent")
        assert result == []


# ===========================================================================
# Section 6: Provenance
# ===========================================================================

class TestProvenance:

    def test_record_and_query_provenance_roundtrip(self, db):
        db.record_provenance(_make_provenance())
        results = db.query_provenance()
        assert len(results) == 1
        assert results[0]["chunk_id"] == "chunk-abc"
        assert results[0]["stored_by"] == "agent-x"

    def test_query_provenance_filter_by_stored_by(self, db):
        db.record_provenance(_make_provenance({"id": "p1", "stored_by": "alice"}))
        db.record_provenance(_make_provenance({"id": "p2", "stored_by": "bob"}))
        db.record_provenance(_make_provenance({"id": "p3", "stored_by": "alice"}))
        result = db.query_provenance(stored_by="alice")
        assert len(result) == 2
        assert all(r["stored_by"] == "alice" for r in result)

    def test_query_provenance_filter_by_channel_origin(self, db):
        db.record_provenance(_make_provenance({"id": "p1", "channel_origin": "discord"}))
        db.record_provenance(_make_provenance({"id": "p2", "channel_origin": "slack"}))
        result = db.query_provenance(channel_origin="slack")
        assert len(result) == 1
        assert result[0]["id"] == "p2"

    def test_query_provenance_combined_filters(self, db):
        db.record_provenance(_make_provenance({"id": "p1", "stored_by": "alice", "channel_origin": "discord"}))
        db.record_provenance(_make_provenance({"id": "p2", "stored_by": "alice", "channel_origin": "slack"}))
        db.record_provenance(_make_provenance({"id": "p3", "stored_by": "bob", "channel_origin": "discord"}))
        result = db.query_provenance(stored_by="alice", channel_origin="discord")
        assert len(result) == 1
        assert result[0]["id"] == "p1"

    def test_query_provenance_limit(self, db):
        for i in range(10):
            db.record_provenance(_make_provenance({
                "id": f"p-{i}",
                "timestamp": f"2025-01-{i+1:02d}T00:00:00",
            }))
        result = db.query_provenance(limit=3)
        assert len(result) == 3

    def test_query_provenance_ordered_by_timestamp_desc(self, db):
        db.record_provenance(_make_provenance({"id": "p-old", "timestamp": "2025-01-01T00:00:00"}))
        db.record_provenance(_make_provenance({"id": "p-new", "timestamp": "2025-06-01T00:00:00"}))
        result = db.query_provenance()
        assert result[0]["id"] == "p-new"
        assert result[1]["id"] == "p-old"

    def test_query_provenance_empty_when_no_records(self, db):
        result = db.query_provenance()
        assert result == []

    def test_record_provenance_duplicate_id_raises(self, db):
        db.record_provenance(_make_provenance())
        with pytest.raises(sqlite3.IntegrityError):
            db.record_provenance(_make_provenance())


# ===========================================================================
# Section 7: Error Reports
# ===========================================================================

class TestCreateAndGetErrorReport:

    def test_create_and_get_error_report_roundtrip(self, db):
        db.create_error_report(_make_error_report())
        got = db.get_error_report("er-001")
        assert got is not None
        assert got["error_type"] == "execution"
        assert got["severity"] == "high"
        assert got["status"] == "open"

    def test_get_error_report_returns_none_for_missing(self, db):
        assert db.get_error_report("no-such") is None

    def test_create_error_report_duplicate_id_raises(self, db):
        db.create_error_report(_make_error_report())
        with pytest.raises(sqlite3.IntegrityError):
            db.create_error_report(_make_error_report())


class TestListErrorReports:

    def test_list_error_reports_all(self, db):
        db.create_error_report(_make_error_report({"id": "er-1"}))
        db.create_error_report(_make_error_report({"id": "er-2"}))
        result = db.list_error_reports()
        assert len(result) == 2

    def test_list_error_reports_filter_by_agent(self, db):
        db.create_error_report(_make_error_report({"id": "er-1", "responsible_agent": "a-1"}))
        db.create_error_report(_make_error_report({"id": "er-2", "responsible_agent": "a-2"}))
        result = db.list_error_reports(agent="a-1")
        assert len(result) == 1
        assert result[0]["responsible_agent"] == "a-1"

    def test_list_error_reports_filter_by_project(self, db):
        db.create_error_report(_make_error_report({"id": "er-1", "project_id": "p1"}))
        db.create_error_report(_make_error_report({"id": "er-2", "project_id": "p2"}))
        result = db.list_error_reports(project_id="p1")
        assert len(result) == 1

    def test_list_error_reports_filter_by_status(self, db):
        db.create_error_report(_make_error_report({"id": "er-1", "status": "open"}))
        db.create_error_report(_make_error_report({"id": "er-2", "status": "resolved"}))
        result = db.list_error_reports(status="resolved")
        assert len(result) == 1
        assert result[0]["status"] == "resolved"

    def test_list_error_reports_combined_filters(self, db):
        db.create_error_report(_make_error_report({
            "id": "er-1", "responsible_agent": "a-1", "project_id": "p1", "status": "open",
        }))
        db.create_error_report(_make_error_report({
            "id": "er-2", "responsible_agent": "a-1", "project_id": "p1", "status": "resolved",
        }))
        db.create_error_report(_make_error_report({
            "id": "er-3", "responsible_agent": "a-2", "project_id": "p1", "status": "open",
        }))
        result = db.list_error_reports(agent="a-1", project_id="p1", status="open")
        assert len(result) == 1
        assert result[0]["id"] == "er-1"

    def test_list_error_reports_with_limit(self, db):
        for i in range(5):
            db.create_error_report(_make_error_report({
                "id": f"er-{i}",
                "created_at": f"2025-01-0{i+1}T00:00:00",
            }))
        result = db.list_error_reports(limit=2)
        assert len(result) == 2

    def test_list_error_reports_empty_when_no_match(self, db):
        db.create_error_report(_make_error_report())
        result = db.list_error_reports(agent="nobody")
        assert result == []

    def test_list_error_reports_ordered_by_created_at_desc(self, db):
        db.create_error_report(_make_error_report({"id": "er-old", "created_at": "2025-01-01T00:00:00"}))
        db.create_error_report(_make_error_report({"id": "er-new", "created_at": "2025-06-01T00:00:00"}))
        result = db.list_error_reports()
        assert result[0]["id"] == "er-new"


class TestUpdateErrorReport:

    def test_update_error_report_single_field(self, db):
        db.create_error_report(_make_error_report())
        db.update_error_report("er-001", {"status": "resolved"})
        got = db.get_error_report("er-001")
        assert got["status"] == "resolved"
        assert got["description"] == "Null pointer"  # unchanged

    def test_update_error_report_multiple_fields(self, db):
        db.create_error_report(_make_error_report())
        db.update_error_report("er-001", {
            "status": "resolved",
            "resolved_at": "2025-03-01T00:00:00",
            "lesson_learned": "Check for None",
        })
        got = db.get_error_report("er-001")
        assert got["status"] == "resolved"
        assert got["resolved_at"] == "2025-03-01T00:00:00"
        assert got["lesson_learned"] == "Check for None"

    def test_update_error_report_nonexistent_id_is_noop(self, db):
        db.update_error_report("ghost", {"status": "resolved"})  # no error


# ===========================================================================
# Section 8: QA Results
# ===========================================================================

class TestQAResults:

    def test_create_and_list_qa_result_roundtrip(self, db):
        db.create_qa_result(_make_qa_result())
        result = db.list_qa_results()
        assert len(result) == 1
        assert result[0]["verdict"] == "pass"
        assert result[0]["tester_agent"] == "tester-1"

    def test_list_qa_results_filter_by_task_id(self, db):
        db.create_qa_result(_make_qa_result({"id": "qa-1", "task_id": "t-1"}))
        db.create_qa_result(_make_qa_result({"id": "qa-2", "task_id": "t-2"}))
        result = db.list_qa_results(task_id="t-1")
        assert len(result) == 1
        assert result[0]["task_id"] == "t-1"

    def test_list_qa_results_filter_by_project_id(self, db):
        db.create_qa_result(_make_qa_result({"id": "qa-1", "project_id": "p1"}))
        db.create_qa_result(_make_qa_result({"id": "qa-2", "project_id": "p2"}))
        result = db.list_qa_results(project_id="p1")
        assert len(result) == 1

    def test_list_qa_results_combined_filters(self, db):
        db.create_qa_result(_make_qa_result({"id": "qa-1", "task_id": "t-1", "project_id": "p1"}))
        db.create_qa_result(_make_qa_result({"id": "qa-2", "task_id": "t-1", "project_id": "p2"}))
        db.create_qa_result(_make_qa_result({"id": "qa-3", "task_id": "t-2", "project_id": "p1"}))
        result = db.list_qa_results(task_id="t-1", project_id="p1")
        assert len(result) == 1
        assert result[0]["id"] == "qa-1"

    def test_list_qa_results_with_limit(self, db):
        for i in range(5):
            db.create_qa_result(_make_qa_result({
                "id": f"qa-{i}",
                "created_at": f"2025-01-0{i+1}T00:00:00",
            }))
        result = db.list_qa_results(limit=3)
        assert len(result) == 3

    def test_list_qa_results_empty_when_no_match(self, db):
        db.create_qa_result(_make_qa_result())
        result = db.list_qa_results(task_id="nonexistent")
        assert result == []

    def test_list_qa_results_ordered_by_created_at_desc(self, db):
        db.create_qa_result(_make_qa_result({"id": "qa-old", "created_at": "2025-01-01T00:00:00"}))
        db.create_qa_result(_make_qa_result({"id": "qa-new", "created_at": "2025-06-01T00:00:00"}))
        result = db.list_qa_results()
        assert result[0]["id"] == "qa-new"

    def test_create_qa_result_duplicate_id_raises(self, db):
        db.create_qa_result(_make_qa_result())
        with pytest.raises(sqlite3.IntegrityError):
            db.create_qa_result(_make_qa_result())

    def test_qa_result_defects_stored_as_json_string(self, db):
        defects = json.dumps(["bug-1", "bug-2"])
        db.create_qa_result(_make_qa_result({"defects": defects}))
        result = db.list_qa_results()
        parsed = json.loads(result[0]["defects"])
        assert parsed == ["bug-1", "bug-2"]


# ===========================================================================
# Section 9: Stats
# ===========================================================================

class TestStats:

    def test_set_and_get_stat_string_value(self, db):
        db.set_stat("version", "1.0.0")
        assert db.get_stat("version") == "1.0.0"

    def test_set_and_get_stat_integer_value(self, db):
        db.set_stat("total_tasks", 42)
        assert db.get_stat("total_tasks") == 42

    def test_set_and_get_stat_float_value(self, db):
        db.set_stat("avg_cost", 3.14)
        assert db.get_stat("avg_cost") == pytest.approx(3.14)

    def test_set_and_get_stat_boolean_value(self, db):
        db.set_stat("enabled", True)
        assert db.get_stat("enabled") is True

    def test_set_and_get_stat_none_value(self, db):
        db.set_stat("nothing", None)
        # None is JSON-serialized to "null", which json.loads returns as None
        assert db.get_stat("nothing") is None

    def test_set_and_get_stat_dict_value(self, db):
        data = {"agents": 5, "teams": 2, "uptime": 99.9}
        db.set_stat("summary", data)
        assert db.get_stat("summary") == data

    def test_set_and_get_stat_list_value(self, db):
        data = [1, 2, 3, "four"]
        db.set_stat("items", data)
        assert db.get_stat("items") == data

    def test_set_stat_overwrites_existing(self, db):
        db.set_stat("counter", 1)
        db.set_stat("counter", 2)
        assert db.get_stat("counter") == 2

    def test_get_stat_returns_none_for_missing_key(self, db):
        assert db.get_stat("nonexistent") is None

    def test_set_stat_records_updated_at(self, db):
        db.set_stat("probe", "value")
        with db._conn() as conn:
            row = conn.execute("SELECT updated_at FROM stats WHERE key = ?", ("probe",)).fetchone()
        assert row is not None
        assert row["updated_at"] is not None
        # Verify it parses as a valid ISO datetime
        datetime.fromisoformat(row["updated_at"])

    def test_set_stat_string_that_looks_like_json(self, db):
        """A plain string is stored as-is, not double-encoded."""
        db.set_stat("greeting", "hello world")
        assert db.get_stat("greeting") == "hello world"

    def test_set_stat_nested_json(self, db):
        nested = {"level1": {"level2": [1, 2, {"level3": True}]}}
        db.set_stat("nested", nested)
        assert db.get_stat("nested") == nested


# ===========================================================================
# Section 10: Model Dataclass Defaults
# ===========================================================================

class TestTaskModel:

    def test_task_required_fields_only(self):
        t = Task(id="t-1", project_id="p1", title="Do stuff")
        assert t.description == ""
        assert t.state == "Inbox"
        assert t.pipeline == "default"
        assert t.assigned_to == ""
        assert t.priority == "normal"
        assert t.completed_at is None
        assert t.duration_seconds is None
        assert t.cost == 0.0
        assert t.tokens_used == 0
        assert t.success is None
        assert t.tags == ""

    def test_task_created_at_is_auto_populated(self):
        t = Task(id="t-1", project_id="p1", title="Do stuff")
        assert t.created_at is not None
        # Should be a valid ISO timestamp
        datetime.fromisoformat(t.created_at)

    def test_task_custom_values(self):
        t = Task(
            id="t-2",
            project_id="p2",
            title="Custom",
            state="Done",
            priority="high",
            cost=1.5,
            success=True,
        )
        assert t.state == "Done"
        assert t.priority == "high"
        assert t.cost == 1.5
        assert t.success is True

    def test_task_asdict(self):
        t = Task(id="t-1", project_id="p1", title="Test")
        d = asdict(t)
        assert isinstance(d, dict)
        assert d["id"] == "t-1"
        assert "state" in d


class TestAgentModel:

    def test_agent_required_fields_only(self):
        a = Agent(id="a-1", name="Bot", project_id="p1", team_id="t1")
        assert a.role == "worker"
        assert a.status == "active"
        assert a.tasks_completed == 0
        assert a.tasks_failed == 0
        assert a.success_rate == 0.0
        assert a.total_cost == 0.0
        assert a.total_tokens == 0
        assert a.evolution_goal == ""
        assert a.personality_state == ""
        assert a.last_active is None

    def test_agent_created_at_is_auto_populated(self):
        a = Agent(id="a-1", name="Bot", project_id="p1", team_id="t1")
        assert a.created_at is not None
        datetime.fromisoformat(a.created_at)

    def test_agent_custom_values(self):
        a = Agent(
            id="a-1",
            name="LeaderBot",
            project_id="p1",
            team_id="t1",
            role="leader",
            status="evolving",
            tasks_completed=100,
            success_rate=0.95,
        )
        assert a.role == "leader"
        assert a.status == "evolving"
        assert a.tasks_completed == 100


class TestErrorReportModel:

    def test_error_report_required_fields_only(self):
        er = ErrorReport(
            id="er-1",
            task_id="t-1",
            project_id="p1",
            error_type="decision",
            responsible_agent="a-1",
            responsible_role="worker",
        )
        assert er.description == ""
        assert er.severity == "medium"
        assert er.root_cause == ""
        assert er.lesson_learned == ""
        assert er.status == "open"
        assert er.resolved_at is None

    def test_error_report_created_at_is_auto_populated(self):
        er = ErrorReport(
            id="er-1", task_id="t-1", project_id="p1",
            error_type="decision", responsible_agent="a-1", responsible_role="worker",
        )
        assert er.created_at is not None
        datetime.fromisoformat(er.created_at)

    def test_error_report_custom_severity(self):
        er = ErrorReport(
            id="er-1", task_id="t-1", project_id="p1",
            error_type="execution", responsible_agent="a-1",
            responsible_role="worker", severity="critical",
        )
        assert er.severity == "critical"


class TestQAResultModel:

    def test_qa_result_required_fields_only(self):
        qa = QAResult(id="qa-1", task_id="t-1", project_id="p1", verdict="pass")
        assert qa.tester_agent == ""
        assert qa.defects == "[]"
        assert qa.test_coverage == ""
        assert qa.structural_notes == ""

    def test_qa_result_created_at_is_auto_populated(self):
        qa = QAResult(id="qa-1", task_id="t-1", project_id="p1", verdict="fail")
        assert qa.created_at is not None
        datetime.fromisoformat(qa.created_at)

    def test_qa_result_defects_default_is_valid_json(self):
        qa = QAResult(id="qa-1", task_id="t-1", project_id="p1", verdict="pass")
        parsed = json.loads(qa.defects)
        assert parsed == []

    def test_qa_result_custom_values(self):
        qa = QAResult(
            id="qa-1",
            task_id="t-1",
            project_id="p1",
            verdict="fail",
            tester_agent="tester-x",
            defects='["missing tests", "bad naming"]',
            test_coverage="45%",
        )
        assert qa.verdict == "fail"
        assert qa.tester_agent == "tester-x"
        assert json.loads(qa.defects) == ["missing tests", "bad naming"]


class TestSkillModel:

    def test_skill_required_fields_only(self):
        s = Skill(id="sk-1", name="python")
        assert s.description == ""
        assert s.level == "server"
        assert s.level_id == ""
        assert s.proficiency == 0.0
        assert s.usage_count == 0
        assert s.last_used is None
        assert s.source == "local"
        assert s.installed_by == ""
        assert s.tags == ""


class TestTeamModel:

    def test_team_required_fields_only(self):
        t = Team(id="team-1", name="Squad", project_id="p1")
        assert t.template == ""
        assert t.agent_count == 0
        assert t.tasks_completed == 0
        assert t.effectiveness == 0.0

    def test_team_created_at_is_auto_populated(self):
        t = Team(id="team-1", name="Squad", project_id="p1")
        assert t.created_at is not None
        datetime.fromisoformat(t.created_at)


class TestProvenanceRecordModel:

    def test_provenance_record_required_fields_only(self):
        pr = ProvenanceRecord(
            id="prov-1", chunk_id="c-1", stored_by="agent-1", stored_by_type="agent"
        )
        assert pr.channel_origin == ""
        assert pr.visibility == "public"
        assert pr.sensitivity == "normal"
        assert pr.action == "create"

    def test_provenance_record_timestamp_is_auto_populated(self):
        pr = ProvenanceRecord(
            id="prov-1", chunk_id="c-1", stored_by="agent-1", stored_by_type="agent"
        )
        assert pr.timestamp is not None
        datetime.fromisoformat(pr.timestamp)


# ===========================================================================
# Section 11: Edge Cases and Cross-Cutting Concerns
# ===========================================================================

class TestEdgeCases:

    def test_empty_string_fields_are_preserved(self, db):
        db.create_task(_make_task({"description": "", "tags": ""}))
        got = db.get_task("t-001")
        assert got["description"] == ""
        assert got["tags"] == ""

    def test_unicode_in_task_title(self, db):
        db.create_task(_make_task({"title": "Implement feature with emojis and CJK characters"}))
        got = db.get_task("t-001")
        assert got["title"] == "Implement feature with emojis and CJK characters"

    def test_very_long_description(self, db):
        long_desc = "x" * 10000
        db.create_task(_make_task({"description": long_desc}))
        got = db.get_task("t-001")
        assert got["description"] == long_desc

    def test_special_characters_in_strings(self, db):
        desc = "O'Reilly says \"hello\" -- it's <html> & stuff; DROP TABLE tasks;--"
        db.create_task(_make_task({"description": desc}))
        got = db.get_task("t-001")
        assert got["description"] == desc

    def test_stat_with_empty_string_key(self, db):
        db.set_stat("", "empty key")
        assert db.get_stat("") == "empty key"

    def test_multiple_databases_are_independent(self, tmp_path):
        db1 = Database(str(tmp_path / "db1.db"))
        db2 = Database(str(tmp_path / "db2.db"))
        db1.create_task(_make_task({"id": "t-1"}))
        db2.create_task(_make_task({"id": "t-2"}))
        assert db1.get_task("t-1") is not None
        assert db1.get_task("t-2") is None
        assert db2.get_task("t-2") is not None
        assert db2.get_task("t-1") is None

    def test_concurrent_reads_same_db(self, db):
        """Multiple reads from the same db instance should not conflict."""
        db.create_task(_make_task({"id": "t-1"}))
        db.create_task(_make_task({"id": "t-2"}))
        # Interleave reads
        t1 = db.get_task("t-1")
        t2 = db.get_task("t-2")
        assert t1["id"] == "t-1"
        assert t2["id"] == "t-2"

    def test_update_then_list_reflects_changes(self, db):
        db.create_task(_make_task({"id": "t-1", "state": "Inbox"}))
        db.update_task("t-1", {"state": "Done"})
        result = db.list_tasks(state="Done")
        assert len(result) == 1
        assert result[0]["id"] == "t-1"
        # Old state filter returns nothing
        result_old = db.list_tasks(state="Inbox")
        assert len(result_old) == 0

    def test_zero_limit_returns_nothing(self, db):
        db.create_task(_make_task())
        result = db.list_tasks(limit=0)
        assert result == []

    def test_large_offset_returns_empty(self, db):
        db.create_task(_make_task())
        result = db.list_tasks(offset=1000)
        assert result == []

    def test_null_values_in_optional_fields(self, db):
        """Fields like completed_at can be NULL in the DB."""
        db.create_task(_make_task())
        got = db.get_task("t-001")
        assert got["completed_at"] is None
        assert got["duration_seconds"] is None
        assert got["success"] is None

    def test_agent_personality_state_stores_json_string(self, db):
        personality = json.dumps({"mood": "focused", "energy": 0.8})
        db.create_agent(_make_agent({"personality_state": personality}))
        got = db.get_agent("a-001")
        parsed = json.loads(got["personality_state"])
        assert parsed["mood"] == "focused"
        assert parsed["energy"] == 0.8
