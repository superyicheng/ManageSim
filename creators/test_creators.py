"""Comprehensive tests for creators modules.

Covers:
  - agent_creator.py (AgentCreator, ROLE_ARCHETYPES)
  - department_creator.py (DepartmentCreator, slugify)
"""

import os
import sys
import json
import yaml
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

# ---------------------------------------------------------------------------
# Ensure the ManageSim root is importable
# ---------------------------------------------------------------------------
MANAGESIM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if MANAGESIM_ROOT not in sys.path:
    sys.path.insert(0, MANAGESIM_ROOT)

from creators.agent_creator import AgentCreator, ROLE_ARCHETYPES
from creators.department_creator import DepartmentCreator, slugify


# =========================================================================
# Helpers
# =========================================================================

class SpyBridge:
    """Lightweight spy that records store_chunk calls."""

    def __init__(self, base_dir="/tmp/spy"):
        self.base_dir = base_dir
        self.calls = []

    def store_chunk(self, **kwargs):
        self.calls.append(kwargs)
        return f"Stored chunk: {kwargs.get('chunk_id', '?')}"


# =========================================================================
# Section 1: slugify
# =========================================================================


class TestSlugify:
    """Tests for the slugify utility."""

    def test_basic_lowercase(self):
        assert slugify("My Project") == "my-project"

    def test_removes_special_chars(self):
        assert slugify("Project! @#$% Name") == "project-name"

    def test_collapses_multiple_hyphens(self):
        assert slugify("a---b") == "a-b"

    def test_strips_leading_trailing_hyphens(self):
        assert slugify("--hello--") == "hello"

    def test_underscores_become_hyphens(self):
        assert slugify("my_cool_project") == "my-cool-project"

    def test_preserves_numbers(self):
        assert slugify("Project 2024") == "project-2024"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_only_special_chars(self):
        assert slugify("@#$!") == ""

    def test_whitespace_handling(self):
        assert slugify("  spaced  out  ") == "spaced-out"


# =========================================================================
# Section 2: ROLE_ARCHETYPES
# =========================================================================


class TestRoleArchetypes:
    """Validate the ROLE_ARCHETYPES dictionary structure."""

    def test_all_expected_roles_exist(self):
        expected = {"leader", "worker", "reviewer", "researcher", "qa_tester", "error_analyst"}
        assert set(ROLE_ARCHETYPES.keys()) == expected

    @pytest.mark.parametrize("role", ROLE_ARCHETYPES.keys())
    def test_archetype_has_required_keys(self, role):
        arch = ROLE_ARCHETYPES[role]
        for key in ("personality", "evolution_goal", "personality_state", "pipeline_role",
                     "can_report_to", "can_delegate_to"):
            assert key in arch, f"{role} missing key: {key}"

    @pytest.mark.parametrize("role", ROLE_ARCHETYPES.keys())
    def test_personality_state_values_in_range(self, role):
        state = ROLE_ARCHETYPES[role]["personality_state"]
        for k, v in state.items():
            assert 0.0 <= v <= 1.0, f"{role}.{k} = {v} out of range"

    @pytest.mark.parametrize("role", ROLE_ARCHETYPES.keys())
    def test_personality_state_has_five_dimensions(self, role):
        state = ROLE_ARCHETYPES[role]["personality_state"]
        expected_dims = {"rigor", "creativity", "verbosity", "risk_tolerance", "obedience"}
        assert set(state.keys()) == expected_dims

    def test_qa_tester_pipeline_role(self):
        assert ROLE_ARCHETYPES["qa_tester"]["pipeline_role"] == "QA_TESTER"

    def test_error_analyst_pipeline_role(self):
        assert ROLE_ARCHETYPES["error_analyst"]["pipeline_role"] == "ERROR_ANALYST"

    def test_leader_can_delegate_to_reviewer_and_worker(self):
        assert "reviewer" in ROLE_ARCHETYPES["leader"]["can_delegate_to"]
        assert "worker" in ROLE_ARCHETYPES["leader"]["can_delegate_to"]

    def test_worker_cannot_delegate(self):
        assert ROLE_ARCHETYPES["worker"]["can_delegate_to"] == []


# =========================================================================
# Section 3: AgentCreator
# =========================================================================


class TestAgentCreatorInit:
    """Test AgentCreator initialization."""

    def test_default_asset_base_url(self, tmp_path):
        with patch("creators.agent_creator.EasybaseBridge", return_value=SpyBridge()):
            ac = AgentCreator(easybase_dir=str(tmp_path))
        assert ac.asset_base_url == "http://localhost:8100"

    def test_custom_asset_base_url(self, tmp_path):
        with patch("creators.agent_creator.EasybaseBridge", return_value=SpyBridge()):
            ac = AgentCreator(easybase_dir=str(tmp_path), asset_base_url="http://custom:9999")
        assert ac.asset_base_url == "http://custom:9999"


class TestAgentCreatorCreateAgent:
    """Test AgentCreator.create_agent."""

    @pytest.fixture()
    def creator(self, tmp_path):
        spy = SpyBridge(str(tmp_path))
        with patch("creators.agent_creator.EasybaseBridge", return_value=spy):
            ac = AgentCreator(easybase_dir=str(tmp_path))
            ac.bridge = spy
            ac._register_in_asset_base = MagicMock()  # Don't call real API
            yield ac

    def test_create_agent_returns_expected_keys(self, creator):
        result = creator.create_agent(
            project_id="proj-1", team_id="team-main", name="Alice", role="worker"
        )
        for key in ("agent_id", "name", "role", "project_id", "team_id",
                     "evolution_goal", "personality_state", "task", "created_at", "message"):
            assert key in result

    def test_agent_id_format(self, creator):
        result = creator.create_agent(
            project_id="my-proj", team_id="team-1", name="Bob Smith"
        )
        assert result["agent_id"] == "agent-my-proj-bob-smith"

    def test_default_role_is_worker(self, creator):
        result = creator.create_agent(
            project_id="p", team_id="t", name="X"
        )
        assert result["role"] == "worker"

    def test_custom_personality_overrides_archetype(self, creator):
        result = creator.create_agent(
            project_id="p", team_id="t", name="Custom",
            role="leader", personality="My custom personality"
        )
        # The init_agent call should use the custom personality
        # Check the spy bridge calls
        soul_call = creator.bridge.calls[0]  # init_agent stores soul.md
        assert "My custom personality" in soul_call.get("body", "")

    def test_custom_goal_overrides_archetype(self, creator):
        result = creator.create_agent(
            project_id="p", team_id="t", name="G",
            role="worker", goal="Custom evolution goal"
        )
        assert result["evolution_goal"] == "Custom evolution goal"

    def test_default_goal_from_archetype(self, creator):
        result = creator.create_agent(
            project_id="p", team_id="t", name="D", role="researcher"
        )
        assert result["evolution_goal"] == ROLE_ARCHETYPES["researcher"]["evolution_goal"]

    def test_personality_state_matches_archetype(self, creator):
        result = creator.create_agent(
            project_id="p", team_id="t", name="R", role="reviewer"
        )
        assert result["personality_state"] == ROLE_ARCHETYPES["reviewer"]["personality_state"]

    def test_unknown_role_falls_back_to_worker(self, creator):
        result = creator.create_agent(
            project_id="p", team_id="t", name="U", role="nonexistent"
        )
        assert result["personality_state"] == ROLE_ARCHETYPES["worker"]["personality_state"]

    @pytest.mark.parametrize("role", ROLE_ARCHETYPES.keys())
    def test_create_agent_for_each_role(self, creator, role):
        result = creator.create_agent(
            project_id="proj", team_id="team", name=f"Agent-{role}", role=role
        )
        assert result["role"] == role
        assert result["personality_state"] == ROLE_ARCHETYPES[role]["personality_state"]

    def test_stores_soul_and_claude_chunks(self, creator):
        creator.create_agent(
            project_id="p", team_id="t", name="S", role="worker"
        )
        # init_agent stores soul.md, then create_agent stores CLAUDE.md
        assert len(creator.bridge.calls) >= 2

    def test_claude_md_chunk_id_format(self, creator):
        creator.create_agent(
            project_id="p", team_id="t", name="C", role="worker"
        )
        claude_call = creator.bridge.calls[-1]  # Last call is CLAUDE.md
        assert claude_call["chunk_id"] == "claude-agent-p-c"

    def test_task_included_in_result(self, creator):
        result = creator.create_agent(
            project_id="p", team_id="t", name="T",
            task="Build the frontend"
        )
        assert result["task"] == "Build the frontend"

    def test_register_in_asset_base_called(self, creator):
        creator.create_agent(project_id="p", team_id="t", name="R")
        creator._register_in_asset_base.assert_called_once()


class TestGenerateClaudeMd:
    """Test _generate_claude_md."""

    @pytest.fixture()
    def creator(self, tmp_path):
        spy = SpyBridge(str(tmp_path))
        with patch("creators.agent_creator.EasybaseBridge", return_value=spy):
            ac = AgentCreator(easybase_dir=str(tmp_path))
            yield ac

    def test_contains_pipeline_role(self, creator):
        arch = ROLE_ARCHETYPES["leader"]
        content = creator._generate_claude_md("agent-x", "leader", arch, "")
        assert "PLANNER" in content

    def test_contains_permissions(self, creator):
        arch = ROLE_ARCHETYPES["worker"]
        content = creator._generate_claude_md("agent-w", "worker", arch, "")
        assert "can_report_to" in content
        assert "can_delegate_to" in content

    def test_contains_progress_protocol(self, creator):
        arch = ROLE_ARCHETYPES["worker"]
        content = creator._generate_claude_md("agent-w", "worker", arch, "")
        assert "managesim-task progress" in content

    def test_task_section_absent_when_empty(self, creator):
        arch = ROLE_ARCHETYPES["worker"]
        content = creator._generate_claude_md("agent-w", "worker", arch, "")
        assert "Current Task" not in content

    def test_task_section_present_when_provided(self, creator):
        arch = ROLE_ARCHETYPES["worker"]
        content = creator._generate_claude_md("agent-w", "worker", arch, "Build API")
        assert "Current Task" in content
        assert "Build API" in content

    def test_agent_id_in_header(self, creator):
        arch = ROLE_ARCHETYPES["leader"]
        content = creator._generate_claude_md("agent-proj-alice", "leader", arch, "")
        assert "agent-proj-alice" in content


class TestListArchetypes:
    """Test AgentCreator.list_archetypes."""

    def test_returns_all_roles(self, tmp_path):
        with patch("creators.agent_creator.EasybaseBridge", return_value=SpyBridge()):
            ac = AgentCreator(easybase_dir=str(tmp_path))
        archetypes = ac.list_archetypes()
        assert set(archetypes.keys()) == set(ROLE_ARCHETYPES.keys())

    def test_archetype_has_personality_and_goal(self, tmp_path):
        with patch("creators.agent_creator.EasybaseBridge", return_value=SpyBridge()):
            ac = AgentCreator(easybase_dir=str(tmp_path))
        for role, info in ac.list_archetypes().items():
            assert "personality" in info
            assert "evolution_goal" in info
            assert "pipeline_role" in info


# =========================================================================
# Section 4: DepartmentCreator
# =========================================================================


class TestDepartmentCreatorInit:
    """Test DepartmentCreator initialization."""

    def test_loads_empty_config_when_file_missing(self, tmp_path):
        config_path = str(tmp_path / "nonexistent.yaml")
        with patch("creators.department_creator.EasybaseBridge", return_value=SpyBridge()):
            dc = DepartmentCreator(config_path=config_path)
        assert dc.config == {}

    def test_loads_existing_config(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump({"projects": [{"id": "old-proj"}]}))
        with patch("creators.department_creator.EasybaseBridge", return_value=SpyBridge()):
            dc = DepartmentCreator(config_path=str(config_path))
        assert len(dc.config["projects"]) == 1


class TestDepartmentCreatorCreateDepartment:
    """Test DepartmentCreator.create_department."""

    @pytest.fixture()
    def dc(self, tmp_path):
        config_path = str(tmp_path / "config" / "managesim.yaml")
        spy = SpyBridge(str(tmp_path))
        with patch("creators.department_creator.EasybaseBridge", return_value=spy):
            # Mock all the init_ functions to avoid real Easybase calls
            with patch("creators.department_creator.init_project") as mp, \
                 patch("creators.department_creator.init_team") as mt, \
                 patch("creators.department_creator.init_agent") as ma, \
                 patch("creators.department_creator.init_qa_team") as mqa, \
                 patch("creators.department_creator.init_error_learning_team") as mel, \
                 patch("creators.department_creator.init_test_team") as mtt, \
                 patch("creators.department_creator.init_error_feedback_team") as mef, \
                 patch("creators.department_creator.init_leader_guide") as mlg, \
                 patch("creators.department_creator.init_vision") as mv:
                creator = DepartmentCreator(config_path=config_path)
                creator._mocks = {
                    "init_project": mp,
                    "init_team": mt,
                    "init_agent": ma,
                    "init_qa_team": mqa,
                    "init_error_learning_team": mel,
                    "init_test_team": mtt,
                    "init_error_feedback_team": mef,
                    "init_leader_guide": mlg,
                    "init_vision": mv,
                }
                yield creator

    def test_create_department_returns_expected_keys(self, dc):
        result = dc.create_department("Test Project")
        for key in ("project_id", "name", "team_id", "leader_id",
                     "qa_team_id", "error_team_id", "test_team_id",
                     "feedback_team_id", "channel_id", "bot_token_env",
                     "created_at", "message"):
            assert key in result, f"Missing key: {key}"

    def test_project_id_is_slugified(self, dc):
        result = dc.create_department("My Cool Project")
        assert result["project_id"] == "my-cool-project"

    def test_team_id_format(self, dc):
        result = dc.create_department("TestProj")
        assert result["team_id"] == "team-testproj-main"

    def test_leader_id_format(self, dc):
        result = dc.create_department("TestProj")
        assert result["leader_id"] == "agent-testproj-leader"

    def test_qa_team_id_format(self, dc):
        result = dc.create_department("TestProj")
        assert result["qa_team_id"] == "team-testproj-qa"

    def test_error_team_id_format(self, dc):
        result = dc.create_department("TestProj")
        assert result["error_team_id"] == "team-testproj-error-learning"

    def test_test_team_id_format(self, dc):
        result = dc.create_department("TestProj")
        assert result["test_team_id"] == "team-testproj-test"

    def test_feedback_team_id_format(self, dc):
        result = dc.create_department("TestProj")
        assert result["feedback_team_id"] == "team-testproj-error-feedback"

    def test_default_channel_id_is_pending(self, dc):
        result = dc.create_department("TestProj")
        assert result["channel_id"] == "<pending>"

    def test_custom_channel_id(self, dc):
        result = dc.create_department("TestProj", channel_id="123456")
        assert result["channel_id"] == "123456"

    def test_auto_generated_bot_token_env(self, dc):
        result = dc.create_department("My Project")
        assert result["bot_token_env"] == "DISCORD_BOT_TOKEN_MY_PROJECT"

    def test_custom_bot_token_env(self, dc):
        result = dc.create_department("X", bot_token_env="MY_TOKEN")
        assert result["bot_token_env"] == "MY_TOKEN"

    def test_init_project_called(self, dc):
        dc.create_department("TestProj")
        dc._mocks["init_project"].assert_called_once()

    def test_init_team_called(self, dc):
        dc.create_department("TestProj")
        dc._mocks["init_team"].assert_called_once()

    def test_init_agent_called_for_leader(self, dc):
        dc.create_department("TestProj")
        dc._mocks["init_agent"].assert_called_once()
        call_kwargs = dc._mocks["init_agent"].call_args
        assert call_kwargs[1]["role"] == "leader" or (
            len(call_kwargs[0]) > 0
        )

    def test_all_five_teams_initialized(self, dc):
        dc.create_department("TestProj")
        dc._mocks["init_qa_team"].assert_called_once()
        dc._mocks["init_error_learning_team"].assert_called_once()
        dc._mocks["init_test_team"].assert_called_once()
        dc._mocks["init_error_feedback_team"].assert_called_once()

    def test_leader_guide_created(self, dc):
        dc.create_department("TestProj")
        dc._mocks["init_leader_guide"].assert_called_once()

    def test_vision_created(self, dc):
        dc.create_department("TestProj")
        dc._mocks["init_vision"].assert_called_once()

    def test_config_saved_with_project_entry(self, dc):
        dc.create_department("TestProj")
        assert len(dc.config["projects"]) == 1
        entry = dc.config["projects"][0]
        assert entry["id"] == "testproj"
        assert entry["name"] == "TestProj"

    def test_config_file_written_to_disk(self, dc):
        dc.create_department("TestProj")
        assert os.path.exists(dc.config_path)
        with open(dc.config_path) as f:
            saved = yaml.safe_load(f)
        assert len(saved["projects"]) == 1

    def test_duplicate_project_returns_error(self, dc):
        dc.create_department("Dup")
        result = dc.create_department("Dup")
        assert "error" in result
        assert "already exists" in result["error"]

    def test_message_mentions_all_teams(self, dc):
        result = dc.create_department("TestProj")
        msg = result["message"].lower()
        assert "leader" in msg
        assert "qa" in msg
        assert "error" in msg
        assert "test" in msg


class TestDepartmentCreatorListAndDelete:
    """Test list_departments and delete_department."""

    @pytest.fixture()
    def dc(self, tmp_path):
        config_path = str(tmp_path / "config" / "managesim.yaml")
        with patch("creators.department_creator.EasybaseBridge", return_value=SpyBridge()), \
             patch("creators.department_creator.init_project"), \
             patch("creators.department_creator.init_team"), \
             patch("creators.department_creator.init_agent"), \
             patch("creators.department_creator.init_qa_team"), \
             patch("creators.department_creator.init_error_learning_team"), \
             patch("creators.department_creator.init_test_team"), \
             patch("creators.department_creator.init_error_feedback_team"), \
             patch("creators.department_creator.init_leader_guide"), \
             patch("creators.department_creator.init_vision"):
            creator = DepartmentCreator(config_path=config_path)
            yield creator

    def test_list_departments_empty(self, dc):
        assert dc.list_departments() == []

    def test_list_departments_after_creation(self, dc):
        dc.create_department("Alpha")
        dc.create_department("Beta")
        depts = dc.list_departments()
        assert len(depts) == 2
        ids = [d["id"] for d in depts]
        assert "alpha" in ids
        assert "beta" in ids

    def test_delete_department_removes_from_config(self, dc):
        dc.create_department("ToDelete")
        assert len(dc.list_departments()) == 1
        dc.delete_department("todelete")
        assert len(dc.list_departments()) == 0

    def test_delete_nonexistent_department_no_error(self, dc):
        result = dc.delete_department("does-not-exist")
        assert result is True

    def test_delete_preserves_other_departments(self, dc):
        dc.create_department("Keep")
        dc.create_department("Remove")
        dc.delete_department("remove")
        depts = dc.list_departments()
        assert len(depts) == 1
        assert depts[0]["id"] == "keep"
