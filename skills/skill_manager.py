"""Skill manager — search, inspect, install, and manage agent skills.

Three-tier skill discovery:
1. Local: Skills in agent workspace directories (SKILL.md format)
2. Curated repos: Pre-configured GitHub sources
3. ClawHub registry: Semantic search across published skills
"""

import os
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional

from .skill_search import SkillSearchEngine
from .security_scanner import SecurityScanner


class SkillInfo:
    def __init__(self, data: dict):
        self.id = data.get("id", "")
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.author = data.get("author", "")
        self.version = data.get("version", "1.0.0")
        self.source = data.get("source", "local")  # local | curated | clawhub
        self.source_url = data.get("source_url", "")
        self.tags = data.get("tags", [])
        self.security_tier = data.get("security_tier", "unknown")  # clean | suspicious | malicious
        self.installed = data.get("installed", False)
        self.installed_at = data.get("installed_at", "")
        self.installed_for = data.get("installed_for", "")  # agent ID

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "source": self.source,
            "source_url": self.source_url,
            "tags": self.tags,
            "security_tier": self.security_tier,
            "installed": self.installed,
            "installed_at": self.installed_at,
            "installed_for": self.installed_for,
        }


class SkillManager:
    def __init__(self, skills_dir: str = "./data/skills", config_path: str = None):
        self.skills_dir = skills_dir
        os.makedirs(skills_dir, exist_ok=True)
        self.search_engine = SkillSearchEngine(config_path)
        self.scanner = SecurityScanner()
        self._installed = self._load_installed()

    def _load_installed(self) -> dict:
        """Load installed skills registry."""
        registry_path = os.path.join(self.skills_dir, "installed.json")
        if os.path.exists(registry_path):
            with open(registry_path) as f:
                return json.load(f)
        return {}

    def _save_installed(self):
        """Save installed skills registry."""
        registry_path = os.path.join(self.skills_dir, "installed.json")
        with open(registry_path, 'w') as f:
            json.dump(self._installed, f, indent=2)

    def search(self, query: str, source: str = "all") -> list[SkillInfo]:
        """Search for skills across all sources.

        Args:
            query: Search query
            source: Filter by source (all, local, curated, clawhub)

        Returns:
            List of matching SkillInfo objects
        """
        results = self.search_engine.search(query, source)
        return [SkillInfo(r) for r in results]

    def inspect(self, skill_id: str) -> Optional[SkillInfo]:
        """Inspect a skill before installation — includes security scan."""
        skill_data = self.search_engine.get_skill(skill_id)
        if not skill_data:
            return None

        skill = SkillInfo(skill_data)

        # Run security scan
        scan_result = self.scanner.scan(skill_data)
        skill.security_tier = scan_result["tier"]

        return skill

    def install(self, skill_id: str, agent_id: str = "") -> dict:
        """Install a skill for a specific agent.

        Args:
            skill_id: ID of the skill to install
            agent_id: Agent to install for (empty = server-wide)

        Returns:
            Installation result
        """
        skill = self.inspect(skill_id)
        if not skill:
            return {"error": f"Skill '{skill_id}' not found"}

        # Security gate
        if skill.security_tier == "malicious":
            return {"error": "Skill blocked: malicious content detected", "skill": skill.to_dict()}

        if skill.security_tier == "suspicious":
            return {
                "warning": "Skill flagged as suspicious — requires admin approval",
                "skill": skill.to_dict(),
                "action": "pending_approval",
            }

        # Install
        install_key = f"{agent_id or 'server'}:{skill_id}"
        self._installed[install_key] = {
            **skill.to_dict(),
            "installed": True,
            "installed_at": datetime.utcnow().isoformat(),
            "installed_for": agent_id,
        }
        self._save_installed()

        return {
            "status": "installed",
            "skill": skill.to_dict(),
            "agent_id": agent_id,
        }

    def uninstall(self, skill_id: str, agent_id: str = "") -> dict:
        """Uninstall a skill."""
        install_key = f"{agent_id or 'server'}:{skill_id}"
        if install_key in self._installed:
            del self._installed[install_key]
            self._save_installed()
            return {"status": "uninstalled", "skill_id": skill_id}
        return {"error": f"Skill '{skill_id}' not installed for {agent_id or 'server'}"}

    def list_installed(self, agent_id: str = "") -> list[SkillInfo]:
        """List installed skills, optionally filtered by agent."""
        results = []
        for key, data in self._installed.items():
            if agent_id and not key.startswith(f"{agent_id}:"):
                # Also include server-wide skills
                if not key.startswith("server:"):
                    continue
            results.append(SkillInfo(data))
        return results

    def update(self, skill_id: str, agent_id: str = "") -> dict:
        """Update an installed skill to latest version."""
        install_key = f"{agent_id or 'server'}:{skill_id}"
        if install_key not in self._installed:
            return {"error": f"Skill '{skill_id}' not installed"}

        # Re-fetch and re-install
        return self.install(skill_id, agent_id)
