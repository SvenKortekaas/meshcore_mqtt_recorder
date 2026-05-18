"""Service registrations for MeshCore MQTT Recorder.

Step 11 — register the get_history service:
  - Parameters: channel, start (optional ISO timestamp), end (optional),
    limit (default 100, max 1000)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_register_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register integration services."""
    # TODO Step 11: register meshcore_mqtt_recorder.get_history
