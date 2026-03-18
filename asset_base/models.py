"""Data models for Asset Base — Task, Skill, Agent, Team, Context, Provenance."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Task:
    id: str
    project_id: str
    title: str
    description: str = ""
    state: str = "Inbox"
    pipeline: str = "default"
    assigned_to: str = ""
    priority: str = "normal"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    cost: float = 0.0
    tokens_used: int = 0
    success: Optional[bool] = None
    tags: str = ""


@dataclass
class Skill:
    id: str
    name: str
    description: str = ""
    level: str = "server"  # server | project | team | agent
    level_id: str = ""  # ID at that level
    proficiency: float = 0.0  # 0.0 to 1.0
    usage_count: int = 0
    last_used: Optional[str] = None
    source: str = "local"  # local | curated | clawhub
    installed_by: str = ""
    tags: str = ""


@dataclass
class Agent:
    id: str
    name: str
    project_id: str
    team_id: str
    role: str = "worker"  # leader | worker | reviewer | researcher
    status: str = "active"  # active | inactive | evolving
    tasks_completed: int = 0
    tasks_failed: int = 0
    success_rate: float = 0.0
    total_cost: float = 0.0
    total_tokens: int = 0
    evolution_goal: str = ""
    personality_state: str = ""  # JSON string of PersonalityState
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_active: Optional[str] = None


@dataclass
class Team:
    id: str
    name: str
    project_id: str
    template: str = ""
    agent_count: int = 0
    tasks_completed: int = 0
    effectiveness: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ErrorReport:
    id: str
    task_id: str
    project_id: str
    error_type: str  # decision | execution | review | integration
    responsible_agent: str
    responsible_role: str
    description: str = ""
    severity: str = "medium"  # low | medium | high | critical
    root_cause: str = ""
    lesson_learned: str = ""
    status: str = "open"  # open | analyzing | resolved
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved_at: Optional[str] = None


@dataclass
class QAResult:
    id: str
    task_id: str
    project_id: str
    verdict: str  # pass | fail | conditional
    tester_agent: str = ""
    defects: str = "[]"  # JSON array of defect descriptions
    test_coverage: str = ""
    structural_notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ProvenanceRecord:
    id: str
    chunk_id: str
    stored_by: str
    stored_by_type: str  # agent | team | user | system
    channel_origin: str = ""
    visibility: str = "public"
    sensitivity: str = "normal"
    action: str = "create"  # create | update | delete
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
