"""MeshCore MQTT Recorder — Home Assistant custom integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform

from .const import _LOGGER
from .coordinator import MeshCoreCoordinator
from .data import MeshCoreData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import MeshCoreConfigEntry

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: MeshCoreConfigEntry) -> bool:
    """Set up MeshCore MQTT Recorder from a config entry."""
    coordinator = MeshCoreCoordinator(hass, entry)
    coordinator.async_start()
    entry.runtime_data = MeshCoreData(coordinator=coordinator)
    _LOGGER.info("MeshCore MQTT Recorder entry set up: %s", entry.entry_id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MeshCoreConfigEntry) -> bool:
    """Unload a config entry."""
    # Background task is cancelled automatically by HA on entry unload.
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
