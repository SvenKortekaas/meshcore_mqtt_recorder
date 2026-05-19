"""Logbook integration for MeshCore MQTT Recorder."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
    LazyEventPartialState,
)
from homeassistant.core import callback
from homeassistant.util import slugify

from .const import DOMAIN, EVENT_MESSAGE_RECEIVED

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant

_LOGBOOK_MSG_MAX = 120


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[
        [str, str, Callable[[LazyEventPartialState], dict[str, str]]], None
    ],
) -> None:
    """Register logbook describer for meshcore_message_received events."""

    @callback
    def _describe(event: LazyEventPartialState) -> dict[str, str]:
        data = event.data
        channel: str = data.get("channel", "")
        sender: str | None = data.get("sender")
        text: str = data.get("text", "")
        preview = text[:_LOGBOOK_MSG_MAX]
        entity_id = f"sensor.{slugify(f'MeshCore {channel}')}"
        return {
            LOGBOOK_ENTRY_NAME: f"MeshCore #{channel}",
            LOGBOOK_ENTRY_MESSAGE: f"{sender or '?'}: {preview}",
            LOGBOOK_ENTRY_ENTITY_ID: entity_id,
        }

    async_describe_event(DOMAIN, EVENT_MESSAGE_RECEIVED, _describe)
