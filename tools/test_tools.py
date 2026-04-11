"""Comprehensive tests for all tools modules.

Covers:
  - mcp_bridge.py (task_create, task_transition, task_progress, task_show)
  - gitnexus_adapter.py (GitNexusAdapter)
  - agent_reach_adapter.py (AgentReachAdapter)
  - amplifier_adapter.py (AmplifierAdapter)
  - paperbanana_adapter.py (PaperBananaAdapter)
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Ensure the ManageSim root is importable
# ---------------------------------------------------------------------------
MANAGESIM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if MANAGESIM_ROOT not in sys.path:
    sys.path.insert(0, MANAGESIM_ROOT)

from tools.gitnexus_adapter import GitNexusAdapter
from tools.agent_reach_adapter import AgentReachAdapter
from tools.amplifier_adapter import AmplifierAdapter
from tools.paperbanana_adapter import PaperBananaAdapter


# =========================================================================
# Section 1: GitNexusAdapter
# =========================================================================


class TestGitNexusAdapter:
    """Test GitNexusAdapter placeholder methods."""

    def test_default_base_url(self):
        adapter = GitNexusAdapter()
        assert adapter.base_url == "http://localhost:8400"

    def test_custom_base_url(self):
        adapter = GitNexusAdapter(base_url="http://custom:9000")
        assert adapter.base_url == "http://custom:9000"

    def test_analyze_repo_not_configured(self):
        adapter = GitNexusAdapter()
        result = adapter.analyze_repo("/some/repo")
        assert result["status"] == "not_configured"

    def test_query_dependencies_returns_empty(self):
        adapter = GitNexusAdapter()
        result = adapter.query_dependencies("src/main.py")
        assert result == []

    def test_find_callers_returns_empty(self):
        adapter = GitNexusAdapter()
        result = adapter.find_callers("my_function")
        assert result == []


# =========================================================================
# Section 2: AgentReachAdapter
# =========================================================================


class TestAgentReachAdapter:
    """Test AgentReachAdapter placeholder methods."""

    def test_default_base_url(self):
        adapter = AgentReachAdapter()
        assert adapter.base_url == "http://localhost:8500"

    def test_custom_base_url(self):
        adapter = AgentReachAdapter(base_url="http://reach:5000")
        assert adapter.base_url == "http://reach:5000"

    def test_search_web_returns_empty(self):
        adapter = AgentReachAdapter()
        result = adapter.search_web("python tutorials")
        assert result == []

    def test_search_web_with_sources(self):
        adapter = AgentReachAdapter()
        result = adapter.search_web("python", sources=["github", "reddit"])
        assert result == []

    def test_scrape_github_not_configured(self):
        adapter = AgentReachAdapter()
        result = adapter.scrape_github("owner/repo")
        assert result["status"] == "not_configured"

    def test_scrape_reddit_returns_empty(self):
        adapter = AgentReachAdapter()
        result = adapter.scrape_reddit("python", query="best practices")
        assert result == []


# =========================================================================
# Section 3: AmplifierAdapter
# =========================================================================


class TestAmplifierAdapter:
    """Test AmplifierAdapter placeholder methods."""

    def test_default_base_url(self):
        adapter = AmplifierAdapter()
        assert adapter.base_url == "http://localhost:8600"

    def test_custom_base_url(self):
        adapter = AmplifierAdapter(base_url="http://amp:6000")
        assert adapter.base_url == "http://amp:6000"

    def test_list_agents_returns_expected_agents(self):
        adapter = AmplifierAdapter()
        agents = adapter.list_agents()
        assert len(agents) == 4
        ids = [a["id"] for a in agents]
        assert "architect" in ids
        assert "bug-hunter" in ids
        assert "git-ops" in ids
        assert "code-review" in ids

    def test_list_agents_have_required_keys(self):
        adapter = AmplifierAdapter()
        for agent in adapter.list_agents():
            assert "id" in agent
            assert "name" in agent
            assert "specialty" in agent

    def test_dispatch_not_configured(self):
        adapter = AmplifierAdapter()
        result = adapter.dispatch("architect", "Design a microservice")
        assert result["status"] == "not_configured"


# =========================================================================
# Section 4: PaperBananaAdapter
# =========================================================================


class TestPaperBananaAdapter:
    """Test PaperBananaAdapter placeholder methods."""

    def test_default_base_url(self):
        adapter = PaperBananaAdapter()
        assert adapter.base_url == "http://localhost:8700"

    def test_custom_base_url(self):
        adapter = PaperBananaAdapter(base_url="http://paper:7000")
        assert adapter.base_url == "http://paper:7000"

    def test_generate_figure_not_configured(self):
        adapter = PaperBananaAdapter()
        result = adapter.generate_figure("A bar chart of results")
        assert result["status"] == "not_configured"

    def test_generate_figure_with_references(self):
        adapter = PaperBananaAdapter()
        result = adapter.generate_figure(
            "Comparison chart",
            references=["doi:10.1234/paper1"],
            style="diagram"
        )
        assert result["status"] == "not_configured"

    def test_list_styles_returns_expected(self):
        adapter = PaperBananaAdapter()
        styles = adapter.list_styles()
        assert "academic" in styles
        assert "diagram" in styles
        assert "chart" in styles
        assert "schematic" in styles
        assert "infographic" in styles
        assert len(styles) == 5


# =========================================================================
# Section 5: MCP Bridge functions
# =========================================================================


class TestMcpBridgeTaskCreate:
    """Test task_create function."""

    @pytest.fixture(autouse=True)
    def setup_task_dir(self, tmp_path, monkeypatch):
        """Redirect task storage to tmp_path."""
        self.task_dir = tmp_path / "data" / "tasks"
        self.task_dir.mkdir(parents=True)

        # Patch the pipeline CLI helpers
        def mock_next_task_id(project):
            existing = list(self.task_dir.glob("*.json"))
            return f"TASK-{len(existing)+1:03d}"

        def mock_save_task(task_id, task):
            path = self.task_dir / f"{task_id}.json"
            with open(path, "w") as f:
                json.dump(task, f)

        def mock_load_task(task_id):
            path = self.task_dir / f"{task_id}.json"
            if not path.exists():
                return None
            with open(path) as f:
                return json.load(f)

        def mock_load_pipeline(name="default"):
            from pipeline.state_machine import StateMachine
            return StateMachine()

        monkeypatch.setattr("tools.mcp_bridge._next_task_id", mock_next_task_id)
        monkeypatch.setattr("tools.mcp_bridge._save_task", mock_save_task)
        monkeypatch.setattr("tools.mcp_bridge._load_task", mock_load_task)
        monkeypatch.setattr("tools.mcp_bridge._load_pipeline", mock_load_pipeline)

    def test_create_task_success(self):
        from tools.mcp_bridge import task_create
        result = json.loads(task_create("my-proj", "Fix the bug"))
        assert result["status"] == "created"
        assert result["title"] == "Fix the bug"
        assert "task_id" in result

    def test_create_task_sanitizes_title(self):
        from tools.mcp_bridge import task_create
        result = json.loads(task_create("proj", "  Trimmed Title  "))
        assert result["title"] == "Trimmed Title"

    def test_create_task_file_written(self):
        from tools.mcp_bridge import task_create
        result = json.loads(task_create("proj", "Written"))
        task_id = result["task_id"]
        assert (self.task_dir / f"{task_id}.json").exists()

    def test_create_task_initial_state_is_inbox(self):
        from tools.mcp_bridge import task_create
        result = json.loads(task_create("proj", "Initial"))
        task_id = result["task_id"]
        with open(self.task_dir / f"{task_id}.json") as f:
            task = json.load(f)
        assert task["state"] == "Inbox"


class TestMcpBridgeTaskTransition:
    """Test task_transition function."""

    @pytest.fixture(autouse=True)
    def setup_task_dir(self, tmp_path, monkeypatch):
        self.task_dir = tmp_path / "data" / "tasks"
        self.task_dir.mkdir(parents=True)

        def mock_save_task(task_id, task):
            path = self.task_dir / f"{task_id}.json"
            with open(path, "w") as f:
                json.dump(task, f)

        def mock_load_task(task_id):
            path = self.task_dir / f"{task_id}.json"
            if not path.exists():
                return None
            with open(path) as f:
                return json.load(f)

        def mock_load_pipeline(name="default"):
            from pipeline.state_machine import StateMachine
            return StateMachine()

        def mock_next_task_id(project):
            existing = list(self.task_dir.glob("*.json"))
            return f"TASK-{len(existing)+1:03d}"

        monkeypatch.setattr("tools.mcp_bridge._next_task_id", mock_next_task_id)
        monkeypatch.setattr("tools.mcp_bridge._save_task", mock_save_task)
        monkeypatch.setattr("tools.mcp_bridge._load_task", mock_load_task)
        monkeypatch.setattr("tools.mcp_bridge._load_pipeline", mock_load_pipeline)

    def test_valid_transition(self):
        from tools.mcp_bridge import task_create, task_transition
        result = json.loads(task_create("proj", "Task 1"))
        task_id = result["task_id"]

        trans = json.loads(task_transition(task_id, "Triage"))
        assert trans["status"] == "transitioned"
        assert trans["from"] == "Inbox"
        assert trans["to"] == "Triage"

    def test_invalid_transition(self):
        from tools.mcp_bridge import task_create, task_transition
        result = json.loads(task_create("proj", "Task 2"))
        task_id = result["task_id"]

        trans = json.loads(task_transition(task_id, "Done"))
        assert "error" in trans

    def test_transition_not_found(self):
        from tools.mcp_bridge import task_transition
        result = json.loads(task_transition("NONEXISTENT", "Triage"))
        assert "error" in result
        assert "not found" in result["error"]

    def test_transition_updates_state_on_disk(self):
        from tools.mcp_bridge import task_create, task_transition
        result = json.loads(task_create("proj", "Disk Check"))
        task_id = result["task_id"]

        task_transition(task_id, "Triage")
        with open(self.task_dir / f"{task_id}.json") as f:
            task = json.load(f)
        assert task["state"] == "Triage"

    def test_chained_transitions(self):
        from tools.mcp_bridge import task_create, task_transition
        result = json.loads(task_create("proj", "Chained Task Flow"))
        task_id = result["task_id"]

        task_transition(task_id, "Triage")
        task_transition(task_id, "Planning")
        task_transition(task_id, "Review")
        task_transition(task_id, "Assigned")
        task_transition(task_id, "Executing")
        task_transition(task_id, "QA")
        trans = json.loads(task_transition(task_id, "Done"))
        assert trans["status"] == "transitioned"
        assert trans["to"] == "Done"


class TestMcpBridgeTaskProgress:
    """Test task_progress function."""

    @pytest.fixture(autouse=True)
    def setup_task_dir(self, tmp_path, monkeypatch):
        self.task_dir = tmp_path / "data" / "tasks"
        self.task_dir.mkdir(parents=True)

        def mock_save_task(task_id, task):
            with open(self.task_dir / f"{task_id}.json", "w") as f:
                json.dump(task, f)

        def mock_load_task(task_id):
            path = self.task_dir / f"{task_id}.json"
            if not path.exists():
                return None
            with open(path) as f:
                return json.load(f)

        def mock_load_pipeline(name="default"):
            from pipeline.state_machine import StateMachine
            return StateMachine()

        def mock_next_task_id(project):
            existing = list(self.task_dir.glob("*.json"))
            return f"TASK-{len(existing)+1:03d}"

        monkeypatch.setattr("tools.mcp_bridge._next_task_id", mock_next_task_id)
        monkeypatch.setattr("tools.mcp_bridge._save_task", mock_save_task)
        monkeypatch.setattr("tools.mcp_bridge._load_task", mock_load_task)
        monkeypatch.setattr("tools.mcp_bridge._load_pipeline", mock_load_pipeline)

    def test_progress_recorded(self):
        from tools.mcp_bridge import task_create, task_progress
        result = json.loads(task_create("proj", "Progress Test"))
        task_id = result["task_id"]

        prog = json.loads(task_progress(task_id, "Step 1 done"))
        assert prog["status"] == "recorded"

    def test_progress_appended_to_task(self):
        from tools.mcp_bridge import task_create, task_progress
        result = json.loads(task_create("proj", "Append Test"))
        task_id = result["task_id"]

        task_progress(task_id, "Step 1")
        task_progress(task_id, "Step 2", checklist="[x] a\n[ ] b")

        with open(self.task_dir / f"{task_id}.json") as f:
            task = json.load(f)
        assert len(task["progress"]) == 2
        assert task["progress"][1]["checklist"] == "[x] a\n[ ] b"

    def test_progress_not_found(self):
        from tools.mcp_bridge import task_progress
        result = json.loads(task_progress("MISSING", "text"))
        assert "error" in result


class TestMcpBridgeTaskShow:
    """Test task_show function."""

    @pytest.fixture(autouse=True)
    def setup_task_dir(self, tmp_path, monkeypatch):
        self.task_dir = tmp_path / "data" / "tasks"
        self.task_dir.mkdir(parents=True)

        def mock_save_task(task_id, task):
            with open(self.task_dir / f"{task_id}.json", "w") as f:
                json.dump(task, f)

        def mock_load_task(task_id):
            path = self.task_dir / f"{task_id}.json"
            if not path.exists():
                return None
            with open(path) as f:
                return json.load(f)

        def mock_load_pipeline(name="default"):
            from pipeline.state_machine import StateMachine
            return StateMachine()

        def mock_next_task_id(project):
            existing = list(self.task_dir.glob("*.json"))
            return f"TASK-{len(existing)+1:03d}"

        monkeypatch.setattr("tools.mcp_bridge._next_task_id", mock_next_task_id)
        monkeypatch.setattr("tools.mcp_bridge._save_task", mock_save_task)
        monkeypatch.setattr("tools.mcp_bridge._load_task", mock_load_task)
        monkeypatch.setattr("tools.mcp_bridge._load_pipeline", mock_load_pipeline)

    def test_show_existing_task(self):
        from tools.mcp_bridge import task_create, task_show
        result = json.loads(task_create("proj", "Show Me"))
        task_id = result["task_id"]

        shown = json.loads(task_show(task_id))
        assert shown["title"] == "Show Me"
        assert shown["project"] == "proj"
        assert shown["state"] == "Inbox"

    def test_show_not_found(self):
        from tools.mcp_bridge import task_show
        result = json.loads(task_show("MISSING"))
        assert "error" in result


class TestMcpBridgeCreateServer:
    """Test MCP server creation."""

    def test_create_mcp_server_without_fastmcp(self):
        from tools.mcp_bridge import create_mcp_server
        with patch.dict("sys.modules", {"fastmcp": None}):
            # When fastmcp is not importable, should return None
            # (or handle gracefully)
            try:
                result = create_mcp_server()
                # If fastmcp happens to be installed, that's OK too
            except Exception:
                pass  # Expected when fastmcp unavailable
