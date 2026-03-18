"""Skill search — hybrid semantic + keyword search across skill sources."""

import os
import json
import yaml
from pathlib import Path
from typing import Optional


class SkillSearchEngine:
    def __init__(self, config_path: str = None):
        self.curated_sources = self._load_curated_sources(config_path)
        self._cache = {}  # Simple in-memory cache

    def _load_curated_sources(self, config_path: str = None) -> list:
        """Load curated skill sources from config."""
        sources_path = config_path or os.path.join(
            os.path.dirname(__file__), "curated_sources.yaml"
        )
        if os.path.exists(sources_path):
            with open(sources_path) as f:
                data = yaml.safe_load(f) or {}
                return data.get("sources", [])
        return []

    def search(self, query: str, source: str = "all") -> list[dict]:
        """Search for skills across configured sources.

        Args:
            query: Search terms
            source: Filter — all, local, curated, clawhub

        Returns:
            List of skill data dicts ranked by relevance
        """
        results = []
        query_terms = query.lower().split()

        if source in ("all", "local"):
            results.extend(self._search_local(query_terms))

        if source in ("all", "curated"):
            results.extend(self._search_curated(query_terms))

        # ClawHub would be an API call — placeholder
        if source in ("all", "clawhub"):
            results.extend(self._search_clawhub(query_terms))

        # Deduplicate and sort by relevance
        seen = set()
        unique = []
        for r in sorted(results, key=lambda x: x.get("_score", 0), reverse=True):
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(r)

        return unique

    def get_skill(self, skill_id: str) -> Optional[dict]:
        """Get a specific skill by ID."""
        # Check cache
        if skill_id in self._cache:
            return self._cache[skill_id]

        # Search all sources
        for result in self.search(skill_id):
            if result["id"] == skill_id:
                self._cache[skill_id] = result
                return result
        return None

    def _search_local(self, query_terms: list) -> list[dict]:
        """Search local SKILL.md files."""
        results = []
        skills_dirs = [
            os.path.expanduser("~/.managesim/skills"),
            "./skills/local",
        ]

        for skills_dir in skills_dirs:
            if not os.path.exists(skills_dir):
                continue
            for fname in os.listdir(skills_dir):
                if not fname.endswith(".md"):
                    continue
                try:
                    path = os.path.join(skills_dir, fname)
                    with open(path) as f:
                        content = f.read()
                    skill = self._parse_skill_md(content, fname)
                    if skill:
                        skill["source"] = "local"
                        skill["_score"] = self._score(skill, query_terms)
                        if skill["_score"] > 0:
                            results.append(skill)
                except (OSError, IOError):
                    continue

        return results

    def _search_curated(self, query_terms: list) -> list[dict]:
        """Search curated GitHub sources (uses cached index)."""
        results = []
        for source in self.curated_sources:
            for skill in source.get("skills", []):
                skill["source"] = "curated"
                skill["source_url"] = source.get("repo", "")
                skill["_score"] = self._score(skill, query_terms)
                if skill["_score"] > 0:
                    results.append(skill)
        return results

    def _search_clawhub(self, query_terms: list) -> list[dict]:
        """Search ClawHub registry (placeholder — would be API call)."""
        # TODO: Implement ClawHub API integration
        return []

    def _parse_skill_md(self, content: str, filename: str) -> Optional[dict]:
        """Parse a SKILL.md file into a skill data dict."""
        lines = content.strip().split("\n")

        name = filename.replace(".md", "")
        description = ""
        tags = []

        for line in lines:
            if line.startswith("# "):
                name = line[2:].strip()
            elif line.startswith("Description:") or line.startswith("## Description"):
                description = line.split(":", 1)[-1].strip() if ":" in line else ""
            elif line.startswith("Tags:"):
                tags = [t.strip() for t in line.split(":", 1)[-1].split(",")]

        if not description and len(lines) > 1:
            description = lines[1].strip()

        return {
            "id": name.lower().replace(" ", "-"),
            "name": name,
            "description": description,
            "tags": tags,
        }

    def _score(self, skill: dict, query_terms: list) -> float:
        """Score a skill against query terms."""
        searchable = f"{skill.get('name', '')} {skill.get('description', '')} {' '.join(skill.get('tags', []))}".lower()

        score = 0
        for term in query_terms:
            if term in searchable:
                score += 1
            # Bonus for name match
            if term in skill.get("name", "").lower():
                score += 2

        return score
