"""Custom types for MeshCore MQTT Recorder."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


type MeshCoreConfigEntry = ConfigEntry[MeshCoreData]


@dataclass
class MeshCoreData:
    """Runtime data stored on the config entry."""

    # TODO Step 3: coordinator: MeshCoreCoordinator
