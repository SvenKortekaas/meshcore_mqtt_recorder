"""Logbook integration for MeshCore MQTT Recorder.

Step 9 — register a human-readable logbook description for
meshcore_message_received events so they render nicely in the Logbook UI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def async_describe_logbook_events(hass: HomeAssistant) -> None:
    """Register logbook event descriptions."""
    # TODO Step 9: call homeassistant.components.logbook.async_describe_event
    # for EVENT_MESSAGE_RECEIVED, returning a human-readable string per event.
