"""MeshCore MQTT Recorder — Home Assistant custom integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import _LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import MeshCoreConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: MeshCoreConfigEntry) -> bool:
    """Set up MeshCore MQTT Recorder from a config entry."""
    _LOGGER.info("Setting up MeshCore MQTT Recorder entry: %s", entry.entry_id)
    # TODO Step 3: initialise MeshCoreMqttClient and start MQTT connection
    # TODO Step 7: forward entry setup to Platform.SENSOR
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MeshCoreConfigEntry) -> bool:
    """Unload a config entry."""
    # TODO Step 3: stop MeshCoreMqttClient
    # TODO Step 7: unload Platform.SENSOR
    return True
