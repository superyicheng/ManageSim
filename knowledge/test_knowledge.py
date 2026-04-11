"""Comprehensive tests for all knowledge modules.

Covers:
  - easybase_bridge.py (EasybaseBridge)
  - hierarchy_init.py (init_server, init_project, init_team, init_agent, etc.)
  - access_control.py (filter_by_visibility, search_with_access_control)
  - mem0_bridge.py (Mem0Bridge — graceful degradation only)
"""

import os
import sys
import types
import textwrap
from unittest.mock import MagicMock, patch, call
from datetime import datetime

import pytest
import yaml

# ---------------------------------------------------------------------------
# Ensure the ManageSim root is importable
# ---------------------------------------------------------------------------
MANAGESIM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if MANAGESIM_ROOT not in sys.path:
    sys.path.insert(0, MANAGESIM_ROOT)

from knowledge.easybase_bridge import EasybaseBridge
from knowledge.access_control import filter_by_visibility, search_with_access_control
from knowledge import hierarchy_init


# =========================================================================
# Section 1: EasybaseBridge
# =========================================================================


class TestEasybaseBridgeStoreChunk:
    """Tests for EasybaseBridge.store_chunk."""

    def test_store_chunk_creates_file_with_yaml_frontmatter_and_body(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        result = bridge.store_chunk(
            chunk_id="test-001",
            summary="A test chunk",
            body="Hello world",
        )
        chunk_file = tmp_path / "chunks" / "test-001.md"
        assert chunk_file.exists(), "Chunk file should be created"

        content = chunk_file.read_text()
        # Starts with YAML frontmatter delimiters
        assert content.startswith("---\n")
        # Has closing delimiter
        parts = content.split("---", 2)
        assert len(parts) >= 3, "Should have opening ---, YAML, closing ---"

        # Parse YAML section
        meta = yaml.safe_load(parts[1])
        assert meta["id"] == "test-001"
        assert meta["summary"] == "A test chunk"
        assert meta["stored_by"] == "system"
        assert meta["visibility"] == "public"
        assert meta["sensitivity"] == "normal"
        assert "updated" in meta

        # Body comes after the closing ---
        body_text = parts[2].strip()
        assert body_text == "Hello world"

        # Return value
        assert "test-001" in result

    def test_store_chunk_with_all_provenance_fields(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(
            chunk_id="prov-001",
            summary="Provenance test",
            body="Secret stuff",
            domain="backend",
            tags="tag1, tag2",
            depends="dep-001",
            tree_path="server/proj/team",
            stored_by="agent-x",
            stored_by_type="agent",
            channel_origin="proj",
            visibility="team",
            sensitivity="sensitive",
        )
        chunk_file = tmp_path / "chunks" / "prov-001.md"
        content = chunk_file.read_text()
        parts = content.split("---", 2)
        meta = yaml.safe_load(parts[1])

        assert meta["domain"] == "backend"
        assert meta["tags"] == "tag1, tag2"
        assert meta["depends"] == "dep-001"
        assert meta["tree_path"] == "server/proj/team"
        assert meta["stored_by"] == "agent-x"
        assert meta["stored_by_type"] == "agent"
        assert meta["channel_origin"] == "proj"
        assert meta["visibility"] == "team"
        assert meta["sensitivity"] == "sensitive"

    def test_store_chunk_omits_empty_optional_fields(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(chunk_id="min-001", summary="Minimal")

        chunk_file = tmp_path / "chunks" / "min-001.md"
        content = chunk_file.read_text()
        parts = content.split("---", 2)
        meta = yaml.safe_load(parts[1])

        # These should NOT appear when left as empty string defaults
        assert "domain" not in meta
        assert "tags" not in meta
        assert "depends" not in meta
        assert "tree_path" not in meta
        assert "channel_origin" not in meta

        # These are always present
        assert "stored_by" in meta
        assert "visibility" in meta
        assert "sensitivity" in meta

    def test_store_chunk_without_body_has_no_trailing_blank_section(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(chunk_id="nobody-001", summary="No body")

        content = (tmp_path / "chunks" / "nobody-001.md").read_text()
        # The file should end after the closing ---
        assert content.strip().endswith("---")

    def test_store_chunk_creates_tree_symlink(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(
            chunk_id="sym-001",
            summary="Symlinked chunk",
            body="link test",
            tree_path="server/myproj",
        )
        link = tmp_path / "knowledge" / "server" / "myproj" / "sym-001.md"
        assert link.exists() or link.is_symlink()
        # The symlink should point to the actual chunk file
        assert os.path.islink(str(link))
        resolved = os.path.realpath(str(link))
        expected = os.path.realpath(str(tmp_path / "chunks" / "sym-001.md"))
        assert resolved == expected

    def test_store_chunk_overwrites_existing_chunk(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(chunk_id="ow-001", summary="Version 1", body="old")
        bridge.store_chunk(chunk_id="ow-001", summary="Version 2", body="new")

        content = (tmp_path / "chunks" / "ow-001.md").read_text()
        assert "Version 2" in content
        assert "new" in content

    def test_store_chunk_updated_field_is_today(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(chunk_id="date-001", summary="Date test")

        content = (tmp_path / "chunks" / "date-001.md").read_text()
        parts = content.split("---", 2)
        meta = yaml.safe_load(parts[1])
        today = datetime.now().strftime("%Y-%m-%d")
        assert str(meta["updated"]) == today

    def test_store_chunk_return_value_includes_tree_path(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        result = bridge.store_chunk(
            chunk_id="ret-001",
            summary="Return test",
            tree_path="server/proj",
        )
        assert "server/proj" in result

    def test_store_chunk_return_value_root_when_no_tree_path(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        result = bridge.store_chunk(chunk_id="ret-002", summary="Root test")
        assert "root" in result


class TestEasybaseBridgeGetChunk:
    """Tests for EasybaseBridge.get_chunk."""

    def test_get_chunk_returns_parsed_metadata(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(
            chunk_id="get-001",
            summary="Get test",
            body="content here",
            domain="testing",
            tags="one, two",
            tree_path="server/x",
            stored_by="agent-1",
            visibility="project",
        )
        chunk = bridge.get_chunk("get-001")
        assert chunk is not None
        assert chunk["id"] == "get-001"
        assert chunk["summary"] == "Get test"
        assert chunk["body"] == "content here"
        assert chunk["domain"] == "testing"
        assert chunk["visibility"] == "project"
        assert chunk["stored_by"] == "agent-1"

    def test_get_chunk_returns_none_for_missing(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        assert bridge.get_chunk("nonexistent") is None

    def test_get_chunk_returns_none_when_chunks_dir_missing(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        # chunks dir does not exist yet
        assert bridge.get_chunk("anything") is None


class TestParseChunkFile:
    """Tests for EasybaseBridge._parse_chunk_file edge cases."""

    def test_parse_malformed_no_frontmatter(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("Just plain text with no YAML frontmatter.\n")
        assert bridge._parse_chunk_file(str(bad_file)) is None

    def test_parse_malformed_single_delimiter(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bad_file = tmp_path / "single.md"
        bad_file.write_text("---\nid: test\nNo closing delimiter\n")
        assert bridge._parse_chunk_file(str(bad_file)) is None

    def test_parse_malformed_invalid_yaml(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bad_file = tmp_path / "invalid_yaml.md"
        bad_file.write_text("---\n: [invalid yaml\n\t- bad\n---\nbody\n")
        assert bridge._parse_chunk_file(str(bad_file)) is None

    def test_parse_malformed_yaml_is_not_dict(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bad_file = tmp_path / "list.md"
        bad_file.write_text("---\n- item1\n- item2\n---\nbody text\n")
        assert bridge._parse_chunk_file(str(bad_file)) is None

    def test_parse_nonexistent_file(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        assert bridge._parse_chunk_file(str(tmp_path / "ghost.md")) is None

    def test_parse_empty_body(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        f = tmp_path / "empty_body.md"
        f.write_text("---\nid: eb-001\nsummary: empty body\n---\n")
        chunk = bridge._parse_chunk_file(str(f))
        assert chunk is not None
        assert chunk["id"] == "eb-001"
        assert chunk["body"] == ""

    def test_parse_multiline_body(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        f = tmp_path / "multi.md"
        f.write_text("---\nid: ml-001\n---\nLine 1\nLine 2\nLine 3\n")
        chunk = bridge._parse_chunk_file(str(f))
        assert chunk is not None
        assert "Line 1" in chunk["body"]
        assert "Line 3" in chunk["body"]


class TestBasicSearch:
    """Tests for EasybaseBridge._basic_search (fallback keyword search)."""

    @pytest.fixture
    def populated_bridge(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(
            chunk_id="s-alpha",
            summary="Alpha testing framework",
            body="Automated alpha tests",
            tags="alpha, testing",
            tree_path="server/projA",
        )
        bridge.store_chunk(
            chunk_id="s-beta",
            summary="Beta release checklist",
            body="Steps for beta release",
            tags="beta, release",
            tree_path="server/projA/teamX",
        )
        bridge.store_chunk(
            chunk_id="s-gamma",
            summary="Gamma ray analysis",
            body="Physics simulation",
            tags="gamma, physics",
            tree_path="server/projB",
        )
        return bridge

    def test_basic_search_finds_by_keyword_in_summary(self, populated_bridge):
        results = populated_bridge._basic_search("alpha", scope="", top_k=10)
        ids = [r["id"] for r in results]
        assert "s-alpha" in ids

    def test_basic_search_finds_by_keyword_in_tags(self, populated_bridge):
        results = populated_bridge._basic_search("release", scope="", top_k=10)
        ids = [r["id"] for r in results]
        assert "s-beta" in ids

    def test_basic_search_finds_by_keyword_in_body(self, populated_bridge):
        results = populated_bridge._basic_search("simulation", scope="", top_k=10)
        ids = [r["id"] for r in results]
        assert "s-gamma" in ids

    def test_basic_search_respects_scope(self, populated_bridge):
        results = populated_bridge._basic_search("testing", scope="server/projB", top_k=10)
        # "Alpha testing framework" is under server/projA, so it should be excluded
        ids = [r["id"] for r in results]
        assert "s-alpha" not in ids

    def test_basic_search_scope_includes_subtree(self, populated_bridge):
        results = populated_bridge._basic_search("release", scope="server/projA", top_k=10)
        ids = [r["id"] for r in results]
        # s-beta is under server/projA/teamX which starts with server/projA
        assert "s-beta" in ids

    def test_basic_search_returns_empty_for_no_matches(self, populated_bridge):
        results = populated_bridge._basic_search("zzzznotfound", scope="", top_k=10)
        assert results == []

    def test_basic_search_returns_empty_when_chunks_dir_missing(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        # No chunks stored yet, directory does not exist
        results = bridge._basic_search("anything", scope="", top_k=10)
        assert results == []

    def test_basic_search_respects_top_k(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        for i in range(20):
            bridge.store_chunk(
                chunk_id=f"topk-{i:03d}",
                summary=f"Common keyword number {i}",
                body="common keyword",
            )
        results = bridge._basic_search("common", scope="", top_k=5)
        assert len(results) == 5

    def test_basic_search_ranks_by_score(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(
            chunk_id="rank-low",
            summary="Some data analysis",
            body="Report",
        )
        bridge.store_chunk(
            chunk_id="rank-high",
            summary="Data analysis data processing data pipeline",
            body="data-heavy document about data",
            tags="data, analysis",
        )
        results = bridge._basic_search("data analysis", scope="", top_k=10)
        # The chunk with more occurrences of both terms should rank higher
        assert len(results) >= 2
        assert results[0]["id"] == "rank-high"

    def test_basic_search_ignores_non_md_files(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(chunk_id="legit", summary="Searchable chunk", body="findme")
        # Create a non-md file in chunks dir
        (tmp_path / "chunks" / "noise.txt").write_text("findme in txt file")
        results = bridge._basic_search("findme", scope="", top_k=10)
        ids = [r["id"] for r in results]
        assert "legit" in ids
        assert len(results) == 1  # Only the .md file


class TestEasybaseBridgeSearch:
    """Tests for the high-level search() method (subprocess fallback)."""

    def test_search_falls_back_to_basic_search(self, tmp_path):
        """When the subprocess call fails, search falls back to _basic_search."""
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(chunk_id="fb-001", summary="Fallback search test", body="found it")

        # The subprocess to easybase ctx.py will almost certainly fail in test,
        # so it should fall back to _basic_search
        results = bridge.search("fallback search")
        ids = [r["id"] for r in results]
        assert "fb-001" in ids


class TestEasybaseBridgeInit:
    """Tests for EasybaseBridge.__init__ defaults."""

    def test_default_base_dir(self):
        bridge = EasybaseBridge()
        expected = os.path.expanduser("~/.easybase")
        assert bridge.base_dir == expected

    def test_custom_base_dir(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path / "custom"))
        assert bridge.base_dir == str(tmp_path / "custom")

    def test_env_var_base_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EASYBASE_DIR", str(tmp_path / "from_env"))
        bridge = EasybaseBridge()
        assert bridge.base_dir == str(tmp_path / "from_env")

    def test_explicit_overrides_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EASYBASE_DIR", str(tmp_path / "from_env"))
        bridge = EasybaseBridge(base_dir=str(tmp_path / "explicit"))
        assert bridge.base_dir == str(tmp_path / "explicit")


# =========================================================================
# Section 2: hierarchy_init
# =========================================================================


class SpyBridge:
    """A spy replacement for EasybaseBridge that records store_chunk calls."""

    def __init__(self):
        self.calls = []

    def store_chunk(self, **kwargs):
        self.calls.append(kwargs)
        return f"Stored chunk: {kwargs.get('chunk_id', '?')}"

    def get_call_by_id(self, chunk_id):
        for c in self.calls:
            if c.get("chunk_id") == chunk_id:
                return c
        return None

    def get_all_ids(self):
        return [c.get("chunk_id") for c in self.calls]


class TestInitServer:
    """Tests for hierarchy_init.init_server."""

    def test_init_server_creates_server_soul_and_claude(self):
        spy = SpyBridge()
        hierarchy_init.init_server(spy, "TestServer")
        ids = spy.get_all_ids()
        assert "server-soul" in ids
        assert "server-claude" in ids

    def test_init_server_soul_has_correct_metadata(self):
        spy = SpyBridge()
        hierarchy_init.init_server(spy, "MyServer")
        soul = spy.get_call_by_id("server-soul")
        assert "MyServer" in soul["summary"]
        assert soul["domain"] == "context"
        assert soul["tree_path"] == "server"
        assert soul["visibility"] == "public"
        assert soul["stored_by_type"] == "system"

    def test_init_server_claude_has_correct_metadata(self):
        spy = SpyBridge()
        hierarchy_init.init_server(spy, "MyServer")
        claude = spy.get_call_by_id("server-claude")
        assert "MyServer" in claude["summary"]
        assert claude["tree_path"] == "server"
        assert claude["visibility"] == "public"

    def test_init_server_default_name(self):
        spy = SpyBridge()
        hierarchy_init.init_server(spy)
        soul = spy.get_call_by_id("server-soul")
        assert "My Agent Server" in soul["summary"]


class TestInitProject:
    """Tests for hierarchy_init.init_project."""

    def test_init_project_creates_soul_chunk(self):
        spy = SpyBridge()
        hierarchy_init.init_project(spy, "proj-a", "Project Alpha")
        ids = spy.get_all_ids()
        assert "soul-proj-a" in ids

    def test_init_project_soul_has_project_tree_path(self):
        spy = SpyBridge()
        hierarchy_init.init_project(spy, "proj-a", "Project Alpha")
        soul = spy.get_call_by_id("soul-proj-a")
        assert soul["tree_path"] == "server/proj-a"

    def test_init_project_visibility_is_project(self):
        spy = SpyBridge()
        hierarchy_init.init_project(spy, "proj-a", "Project Alpha")
        soul = spy.get_call_by_id("soul-proj-a")
        assert soul["visibility"] == "project"

    def test_init_project_channel_origin_set(self):
        spy = SpyBridge()
        hierarchy_init.init_project(spy, "proj-a", "Project Alpha")
        soul = spy.get_call_by_id("soul-proj-a")
        assert soul["channel_origin"] == "proj-a"

    def test_init_project_summary_includes_name(self):
        spy = SpyBridge()
        hierarchy_init.init_project(spy, "proj-a", "Project Alpha")
        soul = spy.get_call_by_id("soul-proj-a")
        assert "Project Alpha" in soul["summary"]


class TestInitTeam:
    """Tests for hierarchy_init.init_team."""

    def test_init_team_creates_context_chunk(self):
        spy = SpyBridge()
        hierarchy_init.init_team(spy, "proj-a", "team-dev", "Dev Team")
        ids = spy.get_all_ids()
        assert "context-team-dev" in ids

    def test_init_team_tree_path(self):
        spy = SpyBridge()
        hierarchy_init.init_team(spy, "proj-a", "team-dev", "Dev Team")
        ctx = spy.get_call_by_id("context-team-dev")
        assert ctx["tree_path"] == "server/proj-a/team-dev"

    def test_init_team_visibility_is_team(self):
        spy = SpyBridge()
        hierarchy_init.init_team(spy, "proj-a", "team-dev", "Dev Team")
        ctx = spy.get_call_by_id("context-team-dev")
        assert ctx["visibility"] == "team"

    def test_init_team_uses_team_id_as_display_when_no_name(self):
        spy = SpyBridge()
        hierarchy_init.init_team(spy, "proj-a", "team-dev")
        ctx = spy.get_call_by_id("context-team-dev")
        assert "team-dev" in ctx["summary"]


class TestInitAgent:
    """Tests for hierarchy_init.init_agent."""

    def test_init_agent_creates_soul_chunk(self):
        spy = SpyBridge()
        hierarchy_init.init_agent(
            spy, "proj-a", "team-dev", "agent-bob",
            agent_name="Bob", role="developer",
        )
        ids = spy.get_all_ids()
        assert "soul-agent-bob" in ids

    def test_init_agent_tree_path_four_levels(self):
        spy = SpyBridge()
        hierarchy_init.init_agent(spy, "proj-a", "team-dev", "agent-bob")
        soul = spy.get_call_by_id("soul-agent-bob")
        assert soul["tree_path"] == "server/proj-a/team-dev/agent-bob"

    def test_init_agent_visibility_is_agent(self):
        spy = SpyBridge()
        hierarchy_init.init_agent(spy, "proj-a", "team-dev", "agent-bob")
        soul = spy.get_call_by_id("soul-agent-bob")
        assert soul["visibility"] == "agent"

    def test_init_agent_role_in_summary(self):
        spy = SpyBridge()
        hierarchy_init.init_agent(
            spy, "proj-a", "team-dev", "agent-bob",
            agent_name="Bob", role="developer",
        )
        soul = spy.get_call_by_id("soul-agent-bob")
        assert "developer" in soul["summary"]
        assert "Bob" in soul["summary"]

    def test_init_agent_role_in_tags(self):
        spy = SpyBridge()
        hierarchy_init.init_agent(
            spy, "proj-a", "team-dev", "agent-bob", role="developer",
        )
        soul = spy.get_call_by_id("soul-agent-bob")
        assert "developer" in soul["tags"]

    def test_init_agent_defaults_to_agent_id_for_name(self):
        spy = SpyBridge()
        hierarchy_init.init_agent(spy, "p", "t", "agent-x")
        soul = spy.get_call_by_id("soul-agent-x")
        assert "agent-x" in soul["summary"]

    def test_init_agent_default_role_is_worker(self):
        spy = SpyBridge()
        hierarchy_init.init_agent(spy, "p", "t", "agent-x")
        soul = spy.get_call_by_id("soul-agent-x")
        assert "worker" in soul["summary"]


class TestInitQaTeam:
    """Tests for hierarchy_init.init_qa_team."""

    def test_init_qa_team_creates_team_and_agent(self):
        spy = SpyBridge()
        hierarchy_init.init_qa_team(spy, "proj-a", "team-qa", "Project A")
        ids = spy.get_all_ids()
        assert "context-team-qa" in ids
        assert "soul-agent-proj-a-qa-tester" in ids

    def test_init_qa_team_agent_role_is_qa_tester(self):
        spy = SpyBridge()
        hierarchy_init.init_qa_team(spy, "proj-a", "team-qa", "Project A")
        agent = spy.get_call_by_id("soul-agent-proj-a-qa-tester")
        assert "qa_tester" in agent["tags"]

    def test_init_qa_team_uses_project_id_when_no_name(self):
        spy = SpyBridge()
        hierarchy_init.init_qa_team(spy, "proj-a", "team-qa")
        ctx = spy.get_call_by_id("context-team-qa")
        assert "proj-a" in ctx["summary"]


class TestInitErrorLearningTeam:
    """Tests for hierarchy_init.init_error_learning_team."""

    def test_creates_team_and_error_analyst_agent(self):
        spy = SpyBridge()
        hierarchy_init.init_error_learning_team(spy, "proj-b", "team-el", "ProjB")
        ids = spy.get_all_ids()
        assert "context-team-el" in ids
        assert "soul-agent-proj-b-error-analyst" in ids

    def test_error_analyst_role(self):
        spy = SpyBridge()
        hierarchy_init.init_error_learning_team(spy, "proj-b", "team-el", "ProjB")
        agent = spy.get_call_by_id("soul-agent-proj-b-error-analyst")
        assert "error_analyst" in agent["tags"]


class TestInitTestTeam:
    """Tests for hierarchy_init.init_test_team."""

    def test_creates_team_and_test_lead_agent(self):
        spy = SpyBridge()
        hierarchy_init.init_test_team(spy, "proj-c", "team-test", "ProjC")
        ids = spy.get_all_ids()
        assert "context-team-test" in ids
        assert "soul-agent-proj-c-test-lead" in ids

    def test_test_lead_role(self):
        spy = SpyBridge()
        hierarchy_init.init_test_team(spy, "proj-c", "team-test", "ProjC")
        agent = spy.get_call_by_id("soul-agent-proj-c-test-lead")
        assert "test_lead" in agent["tags"]


class TestInitErrorFeedbackTeam:
    """Tests for hierarchy_init.init_error_feedback_team."""

    def test_creates_team_and_error_feedback_lead_agent(self):
        spy = SpyBridge()
        hierarchy_init.init_error_feedback_team(spy, "proj-d", "team-efb", "ProjD")
        ids = spy.get_all_ids()
        assert "context-team-efb" in ids
        assert "soul-agent-proj-d-error-feedback-lead" in ids

    def test_error_feedback_lead_role(self):
        spy = SpyBridge()
        hierarchy_init.init_error_feedback_team(spy, "proj-d", "team-efb", "ProjD")
        agent = spy.get_call_by_id("soul-agent-proj-d-error-feedback-lead")
        assert "error_feedback_lead" in agent["tags"]


class TestInitLeaderGuide:
    """Tests for hierarchy_init.init_leader_guide."""

    def test_stores_leader_guide_chunk(self):
        spy = SpyBridge()
        hierarchy_init.init_leader_guide(spy, "proj-a", "Project Alpha")
        ids = spy.get_all_ids()
        assert "leader-guide-proj-a" in ids

    def test_leader_guide_metadata(self):
        spy = SpyBridge()
        hierarchy_init.init_leader_guide(spy, "proj-a", "Project Alpha")
        guide = spy.get_call_by_id("leader-guide-proj-a")
        assert "Project Alpha" in guide["summary"]
        assert guide["tree_path"] == "server/proj-a"
        assert guide["visibility"] == "project"
        assert "leader" in guide["tags"]

    def test_leader_guide_uses_project_id_when_no_name(self):
        spy = SpyBridge()
        hierarchy_init.init_leader_guide(spy, "proj-a")
        guide = spy.get_call_by_id("leader-guide-proj-a")
        assert "proj-a" in guide["summary"]


class TestInitVision:
    """Tests for hierarchy_init.init_vision."""

    def test_stores_vision_chunk(self):
        spy = SpyBridge()
        hierarchy_init.init_vision(spy, "proj-a", "Project Alpha")
        ids = spy.get_all_ids()
        assert "vision-proj-a" in ids

    def test_vision_metadata(self):
        spy = SpyBridge()
        hierarchy_init.init_vision(spy, "proj-a", "Project Alpha")
        vis = spy.get_call_by_id("vision-proj-a")
        assert "Project Alpha" in vis["summary"]
        assert vis["tree_path"] == "server/proj-a"
        assert vis["visibility"] == "project"
        assert "vision" in vis["tags"]

    def test_vision_uses_project_id_when_no_name(self):
        spy = SpyBridge()
        hierarchy_init.init_vision(spy, "proj-a")
        vis = spy.get_call_by_id("vision-proj-a")
        assert "proj-a" in vis["summary"]


class TestInitFullHierarchy:
    """Tests for hierarchy_init.init_full_hierarchy."""

    def test_creates_all_teams_for_each_project(self):
        spy = SpyBridge()
        config = {
            "server": {"name": "TestServer"},
            "projects": [
                {"id": "proj-x", "name": "Project X"},
            ],
        }
        hierarchy_init.init_full_hierarchy(spy, config)
        ids = spy.get_all_ids()

        # Server level
        assert "server-soul" in ids
        assert "server-claude" in ids

        # Project level
        assert "soul-proj-x" in ids

        # QA team
        assert "context-team-proj-x-qa" in ids
        assert "soul-agent-proj-x-qa-tester" in ids

        # Error-learning team
        assert "context-team-proj-x-error-learning" in ids
        assert "soul-agent-proj-x-error-analyst" in ids

        # Test team
        assert "context-team-proj-x-test" in ids
        assert "soul-agent-proj-x-test-lead" in ids

        # Error-feedback team
        assert "context-team-proj-x-error-feedback" in ids
        assert "soul-agent-proj-x-error-feedback-lead" in ids

        # Leader guide and vision
        assert "leader-guide-proj-x" in ids
        assert "vision-proj-x" in ids

    def test_multiple_projects(self):
        spy = SpyBridge()
        config = {
            "server": {"name": "Multi"},
            "projects": [
                {"id": "p1", "name": "P1"},
                {"id": "p2", "name": "P2"},
            ],
        }
        hierarchy_init.init_full_hierarchy(spy, config)
        ids = spy.get_all_ids()

        # Both projects should have their teams
        assert "soul-p1" in ids
        assert "soul-p2" in ids
        assert "context-team-p1-qa" in ids
        assert "context-team-p2-qa" in ids
        assert "leader-guide-p1" in ids
        assert "leader-guide-p2" in ids
        assert "vision-p1" in ids
        assert "vision-p2" in ids

    def test_empty_projects_list(self):
        spy = SpyBridge()
        config = {"server": {"name": "Empty"}, "projects": []}
        hierarchy_init.init_full_hierarchy(spy, config)
        ids = spy.get_all_ids()
        # Only server-level chunks
        assert "server-soul" in ids
        assert "server-claude" in ids
        assert len(ids) == 2

    def test_default_server_name_when_missing(self):
        spy = SpyBridge()
        config = {"projects": []}
        hierarchy_init.init_full_hierarchy(spy, config)
        soul = spy.get_call_by_id("server-soul")
        assert "My Agent Server" in soul["summary"]

    def test_project_uses_id_as_name_when_name_missing(self):
        spy = SpyBridge()
        config = {
            "projects": [{"id": "bare-proj"}],
        }
        hierarchy_init.init_full_hierarchy(spy, config)
        soul = spy.get_call_by_id("soul-bare-proj")
        assert "bare-proj" in soul["summary"]

    def test_total_chunk_count_for_single_project(self):
        """Each project generates: 1 soul + 4 teams (each = 1 context + 1 agent) + 1 guide + 1 vision = 11.
        Plus 2 server-level chunks = 13 total."""
        spy = SpyBridge()
        config = {
            "server": {"name": "S"},
            "projects": [{"id": "p1", "name": "P1"}],
        }
        hierarchy_init.init_full_hierarchy(spy, config)
        assert len(spy.calls) == 13


# =========================================================================
# Section 3: access_control
# =========================================================================


class TestFilterByVisibilityPublic:
    """Public chunks should be visible to everyone."""

    def test_public_visible_to_any_agent(self):
        chunks = [{"id": "c1", "visibility": "public", "body": "hi"}]
        result = filter_by_visibility(chunks, requester_id="agent-1")
        assert len(result) == 1

    def test_public_visible_to_user(self):
        chunks = [{"id": "c1", "visibility": "public"}]
        result = filter_by_visibility(chunks, requester_id="user-1", requester_type="user")
        assert len(result) == 1

    def test_default_visibility_treated_as_public(self):
        chunks = [{"id": "c1"}]  # No visibility key
        result = filter_by_visibility(chunks, requester_id="agent-1")
        assert len(result) == 1


class TestFilterByVisibilityProject:
    """Project chunks should only be visible to agents in the same project."""

    def test_project_visible_to_same_project(self):
        chunks = [{"id": "c1", "visibility": "project", "channel_origin": "proj-a"}]
        result = filter_by_visibility(
            chunks, requester_id="agent-1", requester_project="proj-a",
        )
        assert len(result) == 1

    def test_project_hidden_from_different_project(self):
        chunks = [{"id": "c1", "visibility": "project", "channel_origin": "proj-a"}]
        result = filter_by_visibility(
            chunks, requester_id="agent-1", requester_project="proj-b",
        )
        assert len(result) == 0

    def test_project_hidden_when_no_requester_project(self):
        chunks = [{"id": "c1", "visibility": "project", "channel_origin": "proj-a"}]
        result = filter_by_visibility(chunks, requester_id="agent-1")
        assert len(result) == 0


class TestFilterByVisibilityTeam:
    """Team chunks should only be visible to agents in the same team."""

    def test_team_visible_to_same_team_via_tree_path(self):
        chunks = [{"id": "c1", "visibility": "team", "tree_path": "server/proj-a/team-x/stuff"}]
        result = filter_by_visibility(
            chunks,
            requester_id="agent-1",
            requester_project="proj-a",
            requester_team="team-x",
        )
        assert len(result) == 1

    def test_team_hidden_from_different_team(self):
        chunks = [{"id": "c1", "visibility": "team", "tree_path": "server/proj-a/team-x"}]
        result = filter_by_visibility(
            chunks,
            requester_id="agent-1",
            requester_project="proj-a",
            requester_team="team-y",
        )
        assert len(result) == 0

    def test_team_hidden_from_different_project(self):
        chunks = [{"id": "c1", "visibility": "team", "tree_path": "server/proj-a/team-x"}]
        result = filter_by_visibility(
            chunks,
            requester_id="agent-1",
            requester_project="proj-b",
            requester_team="team-x",
        )
        assert len(result) == 0

    def test_team_hidden_when_no_team_info(self):
        chunks = [{"id": "c1", "visibility": "team", "tree_path": "server/proj-a/team-x"}]
        result = filter_by_visibility(
            chunks, requester_id="agent-1", requester_project="proj-a",
        )
        assert len(result) == 0

    def test_team_hidden_when_no_project_info(self):
        chunks = [{"id": "c1", "visibility": "team", "tree_path": "server/proj-a/team-x"}]
        result = filter_by_visibility(
            chunks, requester_id="agent-1", requester_team="team-x",
        )
        assert len(result) == 0


class TestFilterByVisibilityAgent:
    """Agent chunks should only be visible to the storing agent."""

    def test_agent_visible_to_storing_agent(self):
        chunks = [{"id": "c1", "visibility": "agent", "stored_by": "agent-bob"}]
        result = filter_by_visibility(chunks, requester_id="agent-bob")
        assert len(result) == 1

    def test_agent_hidden_from_other_agent(self):
        chunks = [{"id": "c1", "visibility": "agent", "stored_by": "agent-bob"}]
        result = filter_by_visibility(chunks, requester_id="agent-alice")
        assert len(result) == 0

    def test_agent_hidden_from_user(self):
        chunks = [{"id": "c1", "visibility": "agent", "stored_by": "agent-bob"}]
        result = filter_by_visibility(
            chunks, requester_id="user-1", requester_type="user",
        )
        assert len(result) == 0


class TestFilterByVisibilityPrivate:
    """Private chunks should only be visible to human users."""

    def test_private_visible_to_user(self):
        chunks = [{"id": "c1", "visibility": "private"}]
        result = filter_by_visibility(
            chunks, requester_id="user-1", requester_type="user",
        )
        assert len(result) == 1

    def test_private_hidden_from_agent(self):
        chunks = [{"id": "c1", "visibility": "private"}]
        result = filter_by_visibility(chunks, requester_id="agent-1")
        assert len(result) == 0

    def test_private_hidden_from_agent_even_if_stored_by_same(self):
        chunks = [{"id": "c1", "visibility": "private", "stored_by": "agent-1"}]
        result = filter_by_visibility(
            chunks, requester_id="agent-1", requester_type="agent",
        )
        assert len(result) == 0


class TestFilterByVisibilityUnknown:
    """Unknown visibility values should be treated as public."""

    def test_unknown_visibility_treated_as_public(self):
        chunks = [{"id": "c1", "visibility": "galactic"}]
        result = filter_by_visibility(chunks, requester_id="agent-1")
        assert len(result) == 1


class TestFilterByVisibilityMixed:
    """Test filtering a mix of visibility levels at once."""

    def test_mixed_visibility_filtering(self):
        chunks = [
            {"id": "pub", "visibility": "public"},
            {"id": "proj", "visibility": "project", "channel_origin": "proj-a"},
            {"id": "team", "visibility": "team", "tree_path": "server/proj-a/team-x"},
            {"id": "agent", "visibility": "agent", "stored_by": "agent-1"},
            {"id": "priv", "visibility": "private"},
        ]
        result = filter_by_visibility(
            chunks,
            requester_id="agent-1",
            requester_project="proj-a",
            requester_team="team-x",
            requester_type="agent",
        )
        result_ids = {c["id"] for c in result}
        assert result_ids == {"pub", "proj", "team", "agent"}
        assert "priv" not in result_ids

    def test_empty_chunks_list(self):
        result = filter_by_visibility([], requester_id="x")
        assert result == []


class TestSearchWithAccessControl:
    """Tests for search_with_access_control."""

    def test_combines_search_and_filter(self, tmp_path):
        """Use a mock bridge to ensure search results include visibility metadata,
        since the real Easybase subprocess may strip visibility from results."""
        mock_bridge = MagicMock()
        mock_bridge.search.return_value = [
            {"id": "pub-doc", "summary": "Public documentation", "visibility": "public"},
            {"id": "priv-doc", "summary": "Private documentation", "visibility": "private"},
        ]
        results = search_with_access_control(
            mock_bridge,
            query="documentation",
            requester_id="agent-1",
            requester_type="agent",
        )
        ids = [r["id"] for r in results]
        assert "pub-doc" in ids
        assert "priv-doc" not in ids

    def test_respects_top_k(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        for i in range(10):
            bridge.store_chunk(
                chunk_id=f"topk-{i}",
                summary=f"Searchable document {i}",
                body="common keyword content",
                visibility="public",
            )
        results = search_with_access_control(
            bridge,
            query="searchable common",
            requester_id="agent-1",
            top_k=3,
        )
        assert len(results) <= 3

    def test_respects_scope(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(
            chunk_id="in-scope",
            summary="Scoped doc",
            body="content here",
            tree_path="server/proj-a",
            visibility="public",
        )
        bridge.store_chunk(
            chunk_id="out-scope",
            summary="Scoped doc other",
            body="content here",
            tree_path="server/proj-b",
            visibility="public",
        )
        results = search_with_access_control(
            bridge,
            query="scoped doc",
            requester_id="agent-1",
            scope="server/proj-a",
        )
        ids = [r["id"] for r in results]
        assert "in-scope" in ids
        assert "out-scope" not in ids

    def test_over_fetches_then_trims(self, tmp_path):
        """search_with_access_control over-fetches by 3x to account for filtering."""
        mock_bridge = MagicMock()
        mock_bridge.search.return_value = [
            {"id": "a", "visibility": "public"},
            {"id": "b", "visibility": "private"},
            {"id": "c", "visibility": "public"},
        ]
        results = search_with_access_control(
            mock_bridge,
            query="test",
            requester_id="agent-1",
            requester_type="agent",
            top_k=5,
        )
        # Should have called search with top_k * 3 = 15
        # Note: search_with_access_control calls bridge.search(query, scope=..., top_k=...)
        # where query is positional
        mock_bridge.search.assert_called_once_with("test", scope="", top_k=15)
        # Private filtered out
        ids = [r["id"] for r in results]
        assert "b" not in ids


# =========================================================================
# Section 4: mem0_bridge (graceful degradation)
# =========================================================================


class TestMem0BridgeDegradation:
    """When mem0 is not installed, Mem0Bridge should degrade gracefully."""

    def _get_bridge_without_mem0(self):
        """Import Mem0Bridge with HAS_MEM0 forced to False."""
        # We patch HAS_MEM0 at the module level
        import knowledge.mem0_bridge as m0_mod
        original = m0_mod.HAS_MEM0
        m0_mod.HAS_MEM0 = False
        try:
            bridge = m0_mod.Mem0Bridge()
        finally:
            m0_mod.HAS_MEM0 = original
        return bridge

    def test_available_is_false(self):
        bridge = self._get_bridge_without_mem0()
        assert bridge.available is False

    def test_memory_is_none(self):
        bridge = self._get_bridge_without_mem0()
        assert bridge.memory is None

    def test_add_memory_returns_none(self):
        bridge = self._get_bridge_without_mem0()
        result = bridge.add_memory("some content", agent_id="a1")
        assert result is None

    def test_search_memory_returns_empty_list(self):
        bridge = self._get_bridge_without_mem0()
        result = bridge.search_memory("query", agent_id="a1")
        assert result == []

    def test_get_agent_memories_returns_empty_list(self):
        bridge = self._get_bridge_without_mem0()
        result = bridge.get_agent_memories("agent-1")
        assert result == []

    def test_extract_and_store_returns_empty_list(self):
        bridge = self._get_bridge_without_mem0()
        result = bridge.extract_and_store("conversation text", agent_id="a1")
        assert result == []

    def test_no_exceptions_on_any_method(self):
        """Call every public method and ensure none raise."""
        bridge = self._get_bridge_without_mem0()
        # None of these should throw
        bridge.add_memory("x")
        bridge.add_memory("x", agent_id="a", user_id="u", session_id="s", metadata={"k": "v"})
        bridge.search_memory("q")
        bridge.search_memory("q", agent_id="a", user_id="u", top_k=3)
        bridge.get_agent_memories("a")
        bridge.get_agent_memories("a", top_k=5)
        bridge.extract_and_store("conv")
        bridge.extract_and_store("conv", agent_id="a", user_id="u")

    def test_init_does_not_call_init_mem0_when_has_mem0_false(self):
        """When HAS_MEM0 is False, _init_mem0 should not be called."""
        import knowledge.mem0_bridge as m0_mod
        original = m0_mod.HAS_MEM0
        m0_mod.HAS_MEM0 = False
        try:
            with patch.object(m0_mod.Mem0Bridge, "_init_mem0") as mock_init:
                bridge = m0_mod.Mem0Bridge()
                mock_init.assert_not_called()
        finally:
            m0_mod.HAS_MEM0 = original


# =========================================================================
# Section 5: Integration-style tests (EasybaseBridge + access_control)
# =========================================================================


class TestEndToEndAccessControl:
    """Integration tests: store chunks via bridge, then filter with access control."""

    def test_store_and_filter_project_visibility(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(
            chunk_id="int-proj",
            summary="Project secret",
            body="Only for proj-a agents",
            visibility="project",
            channel_origin="proj-a",
        )
        chunk = bridge.get_chunk("int-proj")
        assert chunk is not None

        visible = filter_by_visibility(
            [chunk], requester_id="agent-1", requester_project="proj-a",
        )
        assert len(visible) == 1

        hidden = filter_by_visibility(
            [chunk], requester_id="agent-1", requester_project="proj-b",
        )
        assert len(hidden) == 0

    def test_store_and_filter_agent_visibility(self, tmp_path):
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        bridge.store_chunk(
            chunk_id="int-agent",
            summary="Agent private note",
            body="Personal",
            visibility="agent",
            stored_by="agent-bob",
        )
        chunk = bridge.get_chunk("int-agent")

        visible = filter_by_visibility([chunk], requester_id="agent-bob")
        assert len(visible) == 1

        hidden = filter_by_visibility([chunk], requester_id="agent-alice")
        assert len(hidden) == 0

    def test_full_hierarchy_chunks_have_correct_visibility(self, tmp_path):
        """Verify that init_full_hierarchy produces chunks whose visibility
        passes filter_by_visibility correctly."""
        bridge = EasybaseBridge(base_dir=str(tmp_path))
        config = {
            "server": {"name": "TestSrv"},
            "projects": [{"id": "p1", "name": "P1"}],
        }
        hierarchy_init.init_full_hierarchy(bridge, config)

        # Server-level public chunk should be visible to any agent
        server_soul = bridge.get_chunk("server-soul")
        assert server_soul is not None
        result = filter_by_visibility(
            [server_soul], requester_id="random-agent",
        )
        assert len(result) == 1

        # Project-level chunk should only be visible to same project
        proj_soul = bridge.get_chunk("soul-p1")
        assert proj_soul is not None
        visible = filter_by_visibility(
            [proj_soul], requester_id="a", requester_project="p1",
        )
        assert len(visible) == 1
        hidden = filter_by_visibility(
            [proj_soul], requester_id="a", requester_project="other",
        )
        assert len(hidden) == 0
