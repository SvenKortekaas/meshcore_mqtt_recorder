"""MeshCore MQTT Recorder — Home Assistant custom integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import _LOGGER
from .coordinator import MeshCoreCoordinator
from .data import MeshCoreData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import MeshCoreConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: MeshCoreConfigEntry) -> bool:
    """Set up MeshCore MQTT Recorder from a config entry."""
    coordinator = MeshCoreCoordinator(hass, entry)
    coordinator.async_start()
    entry.runtime_data = MeshCoreData(coordinator=coordinator)
    _LOGGER.info("MeshCore MQTT Recorder entry set up: %s", entry.entry_id)
    # TODO Step 7: forward entry setup to Platform.SENSOR
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MeshCoreConfigEntry) -> bool:
    """Unload a config entry."""
    # Background task is cancelled automatically by HA on entry unload.
    # TODO Step 7: unload Platform.SENSOR
    return True
