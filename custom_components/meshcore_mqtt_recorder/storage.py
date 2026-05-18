"""JSONL persistence — append-only history log per channel.

Step 10 — see CLAUDE.md §Long-Term History:
  - Writes to <config>/meshcore_mqtt_recorder/<channel_slug>.jsonl
  - One JSON object per line, UTF-8, no rotation in v1
  - Each line: decoded message + envelope metadata + channel name + Unix epoch timestamp
"""
from __future__ import annotations

from typing import Any


class MeshCoreStorage:
    """Manages the JSONL history files for all configured channels."""

    async def async_append(self, channel_slug: str, record: dict[str, Any]) -> None:
        """Append one decoded message record to the channel's JSONL file."""
        raise NotImplementedError("TODO Step 10")

    async def async_get_history(
        self,
        channel: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return historical records for a channel, optionally filtered by time range."""
        raise NotImplementedError("TODO Step 11")
