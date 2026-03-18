"""Mem0 bridge — semantic conversational memory enhancement layer.

Mem0 enhances Easybase by providing:
- Auto keyword/summary extraction from conversations
- Semantic vector search as fallback when BM25 misses
- Per-agent/user/session memory scoping
"""

import os
from typing import Optional

# Mem0 is optional — graceful degradation if not installed
try:
    from mem0 import Memory
    HAS_MEM0 = True
except ImportError:
    HAS_MEM0 = False


class Mem0Bridge:
    def __init__(self, config=None):
        self.config = config or {}
        self.memory = None
        if HAS_MEM0:
            self._init_mem0()

    def _init_mem0(self):
        """Initialize Mem0 with local storage."""
        try:
            mem0_config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "managesim",
                        "path": self.config.get("local_path", "./data/mem0"),
                    }
                }
            }
            self.memory = Memory.from_config(mem0_config)
        except Exception:
            self.memory = None

    @property
    def available(self):
        return self.memory is not None

    def add_memory(
        self,
        content: str,
        agent_id: str = "",
        user_id: str = "",
        session_id: str = "",
        metadata: dict = None,
    ):
        """Store a conversational memory with scoping."""
        if not self.available:
            return None

        kwargs = {}
        if agent_id:
            kwargs["agent_id"] = agent_id
        if user_id:
            kwargs["user_id"] = user_id
        if session_id:
            kwargs["run_id"] = session_id
        if metadata:
            kwargs["metadata"] = metadata

        try:
            result = self.memory.add(content, **kwargs)
            return result
        except Exception:
            return None

    def search_memory(
        self,
        query: str,
        agent_id: str = "",
        user_id: str = "",
        top_k: int = 5,
    ) -> list[dict]:
        """Semantic search across memories."""
        if not self.available:
            return []

        kwargs = {"limit": top_k}
        if agent_id:
            kwargs["agent_id"] = agent_id
        if user_id:
            kwargs["user_id"] = user_id

        try:
            results = self.memory.search(query, **kwargs)
            return results if isinstance(results, list) else results.get("results", [])
        except Exception:
            return []

    def get_agent_memories(self, agent_id: str, top_k: int = 20) -> list[dict]:
        """Get all memories for a specific agent."""
        if not self.available:
            return []
        try:
            results = self.memory.get_all(agent_id=agent_id, limit=top_k)
            return results if isinstance(results, list) else results.get("results", [])
        except Exception:
            return []

    def extract_and_store(
        self,
        conversation: str,
        agent_id: str = "",
        user_id: str = "",
    ) -> list[dict]:
        """Auto-extract facts from conversation and store as memories.

        Mem0 automatically extracts key facts, preferences, and decisions
        from conversational text.
        """
        if not self.available:
            return []

        messages = [{"role": "user", "content": conversation}]

        kwargs = {}
        if agent_id:
            kwargs["agent_id"] = agent_id
        if user_id:
            kwargs["user_id"] = user_id

        try:
            result = self.memory.add(messages, **kwargs)
            return result if isinstance(result, list) else [result]
        except Exception:
            return []
