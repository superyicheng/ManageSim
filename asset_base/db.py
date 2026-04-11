"""SQLite database layer for Asset Base structured data."""

import sqlite3
import json
import os
from contextlib import contextmanager
from typing import Optional


class Database:
    def __init__(self, db_path="./data/asset_base.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_tables()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_tables(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    state TEXT DEFAULT 'Inbox',
                    pipeline TEXT DEFAULT 'default',
                    assigned_to TEXT DEFAULT '',
                    priority TEXT DEFAULT 'normal',
                    created_at TEXT,
                    completed_at TEXT,
                    duration_seconds REAL,
                    cost REAL DEFAULT 0.0,
                    tokens_used INTEGER DEFAULT 0,
                    success INTEGER,
                    tags TEXT DEFAULT '',
                    parent_task TEXT DEFAULT '',
                    sub_tasks TEXT DEFAULT '[]',
                    brief TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    level TEXT DEFAULT 'server',
                    level_id TEXT DEFAULT '',
                    proficiency REAL DEFAULT 0.0,
                    usage_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    source TEXT DEFAULT 'local',
                    installed_by TEXT DEFAULT '',
                    tags TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    role TEXT DEFAULT 'worker',
                    status TEXT DEFAULT 'active',
                    tasks_completed INTEGER DEFAULT 0,
                    tasks_failed INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    total_cost REAL DEFAULT 0.0,
                    total_tokens INTEGER DEFAULT 0,
                    evolution_goal TEXT DEFAULT '',
                    personality_state TEXT DEFAULT '',
                    created_at TEXT,
                    last_active TEXT
                );

                CREATE TABLE IF NOT EXISTS teams (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    template TEXT DEFAULT '',
                    agent_count INTEGER DEFAULT 0,
                    tasks_completed INTEGER DEFAULT 0,
                    effectiveness REAL DEFAULT 0.0,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS provenance (
                    id TEXT PRIMARY KEY,
                    chunk_id TEXT NOT NULL,
                    stored_by TEXT NOT NULL,
                    stored_by_type TEXT NOT NULL,
                    channel_origin TEXT DEFAULT '',
                    visibility TEXT DEFAULT 'public',
                    sensitivity TEXT DEFAULT 'normal',
                    action TEXT DEFAULT 'create',
                    timestamp TEXT
                );

                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS error_reports (
                    id TEXT PRIMARY KEY,
                    task_id TEXT,
                    project_id TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    responsible_agent TEXT NOT NULL,
                    responsible_role TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    severity TEXT DEFAULT 'medium',
                    root_cause TEXT DEFAULT '',
                    lesson_learned TEXT DEFAULT '',
                    status TEXT DEFAULT 'open',
                    created_at TEXT,
                    resolved_at TEXT
                );

                CREATE TABLE IF NOT EXISTS qa_results (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    tester_agent TEXT DEFAULT '',
                    verdict TEXT NOT NULL,
                    defects TEXT DEFAULT '[]',
                    test_coverage TEXT DEFAULT '',
                    structural_notes TEXT DEFAULT '',
                    created_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
                CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task);
                CREATE INDEX IF NOT EXISTS idx_skills_level ON skills(level, level_id);
                CREATE INDEX IF NOT EXISTS idx_agents_project ON agents(project_id);
                CREATE INDEX IF NOT EXISTS idx_agents_team ON agents(team_id);
                CREATE INDEX IF NOT EXISTS idx_provenance_stored_by ON provenance(stored_by);
                CREATE INDEX IF NOT EXISTS idx_provenance_channel ON provenance(channel_origin);
                CREATE INDEX IF NOT EXISTS idx_error_reports_agent ON error_reports(responsible_agent);
                CREATE INDEX IF NOT EXISTS idx_error_reports_project ON error_reports(project_id);
                CREATE INDEX IF NOT EXISTS idx_qa_results_task ON qa_results(task_id);
            """)

            # Migrate: add delegation columns to existing tasks table
            for col, default in [
                ("parent_task", "''"),
                ("sub_tasks", "'[]'"),
                ("brief", "''"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} TEXT DEFAULT {default}")
                except sqlite3.OperationalError:
                    pass  # Column already exists

    # --- Tasks ---
    def create_task(self, task_dict):
        with self._conn() as conn:
            cols = ", ".join(task_dict.keys())
            placeholders = ", ".join(["?"] * len(task_dict))
            conn.execute(f"INSERT INTO tasks ({cols}) VALUES ({placeholders})", list(task_dict.values()))

    def get_task(self, task_id):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(row) if row else None

    def list_tasks(self, project_id=None, state=None, limit=50, offset=0):
        with self._conn() as conn:
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            if state:
                query += " AND state = ?"
                params.append(state)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def update_task(self, task_id, updates):
        with self._conn() as conn:
            sets = ", ".join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [task_id]
            conn.execute(f"UPDATE tasks SET {sets} WHERE id = ?", values)

    def get_sub_tasks(self, parent_id):
        """Get all sub-tasks for a parent task."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE parent_task = ?", (parent_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Skills ---
    def create_skill(self, skill_dict):
        with self._conn() as conn:
            cols = ", ".join(skill_dict.keys())
            placeholders = ", ".join(["?"] * len(skill_dict))
            conn.execute(f"INSERT OR REPLACE INTO skills ({cols}) VALUES ({placeholders})", list(skill_dict.values()))

    def get_skill(self, skill_id):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
            return dict(row) if row else None

    def list_skills(self, level=None, level_id=None):
        with self._conn() as conn:
            query = "SELECT * FROM skills WHERE 1=1"
            params = []
            if level:
                query += " AND level = ?"
                params.append(level)
            if level_id:
                query += " AND level_id = ?"
                params.append(level_id)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def update_skill_proficiency(self, skill_id, proficiency):
        with self._conn() as conn:
            conn.execute("UPDATE skills SET proficiency = ?, usage_count = usage_count + 1 WHERE id = ?", (proficiency, skill_id))

    # --- Agents ---
    def create_agent(self, agent_dict):
        with self._conn() as conn:
            cols = ", ".join(agent_dict.keys())
            placeholders = ", ".join(["?"] * len(agent_dict))
            conn.execute(f"INSERT INTO agents ({cols}) VALUES ({placeholders})", list(agent_dict.values()))

    def get_agent(self, agent_id):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
            return dict(row) if row else None

    def list_agents(self, project_id=None, team_id=None):
        with self._conn() as conn:
            query = "SELECT * FROM agents WHERE 1=1"
            params = []
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            if team_id:
                query += " AND team_id = ?"
                params.append(team_id)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def update_agent(self, agent_id, updates):
        with self._conn() as conn:
            sets = ", ".join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [agent_id]
            conn.execute(f"UPDATE agents SET {sets} WHERE id = ?", values)

    def get_agent_performance(self, agent_id):
        with self._conn() as conn:
            row = conn.execute("""
                SELECT
                    tasks_completed, tasks_failed, success_rate,
                    total_cost, total_tokens
                FROM agents WHERE id = ?
            """, (agent_id,)).fetchone()
            return dict(row) if row else None

    # --- Teams ---
    def create_team(self, team_dict):
        with self._conn() as conn:
            cols = ", ".join(team_dict.keys())
            placeholders = ", ".join(["?"] * len(team_dict))
            conn.execute(f"INSERT INTO teams ({cols}) VALUES ({placeholders})", list(team_dict.values()))

    def get_team(self, team_id):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
            return dict(row) if row else None

    def list_teams(self, project_id=None):
        with self._conn() as conn:
            query = "SELECT * FROM teams WHERE 1=1"
            params = []
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    # --- Provenance ---
    def record_provenance(self, record_dict):
        with self._conn() as conn:
            cols = ", ".join(record_dict.keys())
            placeholders = ", ".join(["?"] * len(record_dict))
            conn.execute(f"INSERT INTO provenance ({cols}) VALUES ({placeholders})", list(record_dict.values()))

    def query_provenance(self, stored_by=None, channel_origin=None, limit=50):
        with self._conn() as conn:
            query = "SELECT * FROM provenance WHERE 1=1"
            params = []
            if stored_by:
                query += " AND stored_by = ?"
                params.append(stored_by)
            if channel_origin:
                query += " AND channel_origin = ?"
                params.append(channel_origin)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    # --- Error Reports ---
    def create_error_report(self, report_dict):
        with self._conn() as conn:
            cols = ", ".join(report_dict.keys())
            placeholders = ", ".join(["?"] * len(report_dict))
            conn.execute(f"INSERT INTO error_reports ({cols}) VALUES ({placeholders})", list(report_dict.values()))

    def get_error_report(self, report_id):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM error_reports WHERE id = ?", (report_id,)).fetchone()
            return dict(row) if row else None

    def list_error_reports(self, agent=None, project_id=None, status=None, limit=50):
        with self._conn() as conn:
            query = "SELECT * FROM error_reports WHERE 1=1"
            params = []
            if agent:
                query += " AND responsible_agent = ?"
                params.append(agent)
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def update_error_report(self, report_id, updates):
        with self._conn() as conn:
            sets = ", ".join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [report_id]
            conn.execute(f"UPDATE error_reports SET {sets} WHERE id = ?", values)

    # --- QA Results ---
    def create_qa_result(self, result_dict):
        with self._conn() as conn:
            cols = ", ".join(result_dict.keys())
            placeholders = ", ".join(["?"] * len(result_dict))
            conn.execute(f"INSERT INTO qa_results ({cols}) VALUES ({placeholders})", list(result_dict.values()))

    def list_qa_results(self, task_id=None, project_id=None, limit=50):
        with self._conn() as conn:
            query = "SELECT * FROM qa_results WHERE 1=1"
            params = []
            if task_id:
                query += " AND task_id = ?"
                params.append(task_id)
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    # --- Stats ---
    def set_stat(self, key, value):
        from datetime import datetime
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO stats (key, value, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value) if not isinstance(value, str) else value, datetime.utcnow().isoformat())
            )

    def get_stat(self, key):
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM stats WHERE key = ?", (key,)).fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except (json.JSONDecodeError, TypeError):
                    return row["value"]
            return None
