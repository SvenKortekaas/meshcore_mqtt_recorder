"""MeshCore pipeline coordinator — ties MQTT client, envelope parser, and decoder together."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


class MeshCoreCoordinator:
    """Orchestrates the per-message pipeline for one config entry.

    Step 3 — wire MeshCoreMqttClient here.
    Step 4 — add envelope parsing + dedup cache.
    Step 5 — add MeshCoreDecoder + key store.
    Steps 7–10 — fan out to sensor updates, events, logbook, JSONL storage.
    """

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        self.hass = hass
        self.config_entry = config_entry
        # TODO Step 3: create MeshCoreMqttClient
