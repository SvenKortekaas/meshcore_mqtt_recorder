"""JSONL persistence — append-only history log per channel."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.util import slugify

from .const import _LOGGER, STORAGE_SUBDIR

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
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return history for a channel, optionally filtered by time range."""
        raise NotImplementedError("TODO Step 11")


def _sync_append(path: Path, line: str) -> None:
    # POSIX guarantees O_APPEND writes < PIPE_BUF are atomic; our lines are
    # typically <1 KB. Moot here — a single coordinator serialises all writes
    # via sequential awaits in _handle_message.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
