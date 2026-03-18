"""Provenance tracking — who stored what, where, when."""

from datetime import datetime
import uuid
from .db import Database


class ProvenanceTracker:
    def __init__(self, db: Database):
        self.db = db

    def record(
        self,
        chunk_id: str,
        stored_by: str,
        stored_by_type: str = "system",
        channel_origin: str = "",
        visibility: str = "public",
        sensitivity: str = "normal",
        action: str = "create",
    ):
        """Record a provenance entry."""
        record = {
            "id": f"prov-{uuid.uuid4().hex[:12]}",
            "chunk_id": chunk_id,
            "stored_by": stored_by,
            "stored_by_type": stored_by_type,
            "channel_origin": channel_origin,
            "visibility": visibility,
            "sensitivity": sensitivity,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.db.record_provenance(record)
        return record

    def query_by_agent(self, agent_id: str, limit: int = 50):
        return self.db.query_provenance(stored_by=agent_id, limit=limit)

    def query_by_channel(self, channel: str, limit: int = 50):
        return self.db.query_provenance(channel_origin=channel, limit=limit)
