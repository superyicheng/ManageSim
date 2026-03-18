"""Easybase bridge — records chunks with provenance metadata.

Easybase stores chunks as markdown files with YAML frontmatter.
This bridge adds ManageSim-specific provenance fields:
  stored_by, stored_by_type, channel_origin, visibility, sensitivity
"""

import os
import subprocess
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional


DEFAULT_EASYBASE_DIR = os.path.expanduser("~/.easybase")


class EasybaseBridge:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.environ.get("EASYBASE_DIR", DEFAULT_EASYBASE_DIR)

    def store_chunk(
        self,
        chunk_id: str,
        summary: str,
        body: str = "",
        domain: str = "",
        tags: str = "",
        depends: str = "",
        tree_path: str = "",
        stored_by: str = "system",
        stored_by_type: str = "system",  # agent | team | user | system
        channel_origin: str = "",
        visibility: str = "public",  # public | project | team | agent | private
        sensitivity: str = "normal",  # normal | sensitive | private
    ) -> str:
        """Store a chunk in Easybase with provenance metadata.

        Easybase's _add_chunk supports custom YAML frontmatter fields.
        We write the chunk file directly with our provenance fields.
        """
        chunks_dir = os.path.join(self.base_dir, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)

        # Build frontmatter
        frontmatter = {
            "id": chunk_id,
            "summary": summary,
        }
        if domain:
            frontmatter["domain"] = domain
        if tags:
            frontmatter["tags"] = tags
        if depends:
            frontmatter["depends"] = depends
        if tree_path:
            frontmatter["tree_path"] = tree_path

        # Provenance fields
        frontmatter["stored_by"] = stored_by
        frontmatter["stored_by_type"] = stored_by_type
        if channel_origin:
            frontmatter["channel_origin"] = channel_origin
        frontmatter["visibility"] = visibility
        frontmatter["sensitivity"] = sensitivity
        frontmatter["updated"] = datetime.now().strftime("%Y-%m-%d")

        # Build chunk file content
        lines = ["---"]
        for key, value in frontmatter.items():
            lines.append(f"{key}: {value}")
        lines.append("---")
        if body:
            lines.append("")
            lines.append(body)

        # Write chunk file
        chunk_path = os.path.join(chunks_dir, f"{chunk_id}.md")
        with open(chunk_path, "w") as f:
            f.write("\n".join(lines) + "\n")

        # Create tree_path symlink if specified
        if tree_path:
            self._create_tree_symlink(chunk_id, tree_path)

        # Trigger index rebuild
        self._rebuild_index()

        return f"Stored chunk: {chunk_id} at {tree_path or 'root'}"

    def search(self, query: str, scope: str = "", top_k: int = 10) -> list[dict]:
        """Search Easybase chunks. Returns list of chunk metadata dicts."""
        try:
            cmd = [
                "python3", "-c",
                f"import sys; sys.path.insert(0, '{self._find_easybase_src()}'); "
                f"from ctx import _search_results; "
                f"results = _search_results('{query}', base_dir='{self.base_dir}', "
                f"top_k={top_k}, scope='{scope}' if '{scope}' else None); "
                f"import json; print(json.dumps(results))"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass

        # Fallback: basic file-based search
        return self._basic_search(query, scope, top_k)

    def get_chunk(self, chunk_id: str) -> Optional[dict]:
        """Get a specific chunk by ID."""
        chunk_path = os.path.join(self.base_dir, "chunks", f"{chunk_id}.md")
        if not os.path.exists(chunk_path):
            return None
        return self._parse_chunk_file(chunk_path)

    def _create_tree_symlink(self, chunk_id, tree_path):
        """Create a symlink in the knowledge tree for this chunk."""
        knowledge_dir = os.path.join(self.base_dir, "knowledge")
        tree_dir = os.path.join(knowledge_dir, tree_path)
        os.makedirs(tree_dir, exist_ok=True)

        link_path = os.path.join(tree_dir, f"{chunk_id}.md")
        chunk_path = os.path.join(self.base_dir, "chunks", f"{chunk_id}.md")

        # Remove existing symlink
        if os.path.exists(link_path) or os.path.islink(link_path):
            os.unlink(link_path)

        # Create relative symlink
        rel_path = os.path.relpath(chunk_path, tree_dir)
        os.symlink(rel_path, link_path)

    def _rebuild_index(self):
        """Trigger Easybase index rebuild."""
        try:
            easybase_src = self._find_easybase_src()
            subprocess.run(
                ["python3", "-c",
                 f"import sys; sys.path.insert(0, '{easybase_src}'); "
                 f"from ctx import _rebuild_index; _rebuild_index('{self.base_dir}')"],
                capture_output=True, timeout=30
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Index rebuild is best-effort

    def _find_easybase_src(self):
        """Find the Easybase source directory."""
        # Check common locations
        candidates = [
            os.path.expanduser("~/Desktop/正经货/Cornell/Open git repos/Easybase"),
            os.path.join(self.base_dir, "src"),
            os.path.dirname(self.base_dir),
        ]
        for c in candidates:
            if os.path.exists(os.path.join(c, "ctx.py")):
                return c
        return candidates[0]  # Default guess

    def _basic_search(self, query, scope, top_k):
        """Fallback search: scan chunk files for keyword matches."""
        chunks_dir = os.path.join(self.base_dir, "chunks")
        if not os.path.exists(chunks_dir):
            return []

        results = []
        query_terms = query.lower().split()

        for fname in os.listdir(chunks_dir):
            if not fname.endswith(".md"):
                continue
            chunk = self._parse_chunk_file(os.path.join(chunks_dir, fname))
            if not chunk:
                continue

            # Scope filtering
            if scope and not chunk.get("tree_path", "").startswith(scope):
                continue

            # Simple keyword matching
            searchable = f"{chunk.get('summary', '')} {chunk.get('tags', '')} {chunk.get('body', '')}".lower()
            score = sum(1 for term in query_terms if term in searchable)
            if score > 0:
                chunk["_score"] = score
                results.append(chunk)

        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results[:top_k]

    def _parse_chunk_file(self, path):
        """Parse a chunk markdown file with YAML frontmatter."""
        try:
            with open(path) as f:
                content = f.read()
        except (OSError, IOError):
            return None

        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            metadata = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            return None

        if not isinstance(metadata, dict):
            return None

        metadata["body"] = parts[2].strip()
        return metadata
