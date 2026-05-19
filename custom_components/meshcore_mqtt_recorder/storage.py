"""JSONL persistence — append-only history log per channel."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.util import slugify

from .const import _LOGGER, HISTORY_DEFAULT_LIMIT, HISTORY_MAX_LIMIT, STORAGE_SUBDIR

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class MeshCoreStorage:
    """Manages the JSONL history files for all configured channels."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Compute base directory; directory is created lazily on first write."""
        self._base_dir = Path(hass.config.path(STORAGE_SUBDIR))

    async def append(self, channel: str, payload: dict[str, object]) -> None:
        """Append one JSON record to <channel_slug>.jsonl."""
        path = self._base_dir / f"{slugify(channel)}.jsonl"
        try:
            line = json.dumps(payload, ensure_ascii=False)
            await asyncio.to_thread(_sync_append, path, line)
        except (OSError, TypeError):
            _LOGGER.warning(
                "meshcore storage: failed to append to %s for channel #%s",
                path,
                channel,
                exc_info=True,
            )
            return
        _LOGGER.debug("meshcore storage: appended to %s", path)

    async def async_get_history(
        self,
        channel: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = HISTORY_DEFAULT_LIMIT,
    ) -> list[dict[str, Any]]:
        """Return up to *limit* records for *channel*, newest first."""
        limit = max(1, min(limit, HISTORY_MAX_LIMIT))
        path = self._base_dir / f"{slugify(channel)}.jsonl"
        start_dt = datetime.fromisoformat(start) if start else None
        end_dt = datetime.fromisoformat(end) if end else None
        try:
            records = await asyncio.to_thread(
                _sync_read_history, path, start_dt, end_dt
            )
        except OSError:
            _LOGGER.warning(
                "meshcore storage: failed to read history from %s", path, exc_info=True
            )
            return []
        return records[:limit]


def _sync_read_history(
    path: Path,
    start_dt: datetime | None,
    end_dt: datetime | None,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            try:
                record: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                _LOGGER.debug("meshcore storage: skipping malformed JSONL line")
                continue
            if start_dt is not None or end_dt is not None:
                try:
                    ts = datetime.fromisoformat(record.get("timestamp", ""))
                    if start_dt is not None and ts < start_dt:
                        continue
                    if end_dt is not None and ts > end_dt:
                        continue
                except (ValueError, TypeError):
                    _LOGGER.debug(
                        "meshcore storage: skipping line with unparseable"
                        " or tz-mismatched timestamp"
                    )
                    continue
            records.append(record)
    records.reverse()  # file is chronological; return newest-first
    return records


def _sync_append(path: Path, line: str) -> None:
    # POSIX guarantees O_APPEND writes < PIPE_BUF are atomic; our lines are
    # typically <1 KB. Moot here — a single coordinator serialises all writes
    # via sequential awaits in _handle_message.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
