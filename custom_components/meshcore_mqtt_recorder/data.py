"""Custom types for MeshCore MQTT Recorder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import MeshCoreCoordinator

type MeshCoreConfigEntry = ConfigEntry[MeshCoreData]


@dataclass
class MeshCoreData:
    """Runtime data stored on the config entry."""

    coordinator: MeshCoreCoordinator
