"""Sensor platform for MeshCore MQTT Recorder.

Step 7 — one sensor entity per configured hashtag channel:
  - State: latest message preview (truncated to 255 chars)
  - Attributes: sender, timestamp, msg_id, full_text, last_messages (last 20),
    snr, rssi, observer, path_length
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import MeshCoreConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MeshCoreConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities for each configured channel."""
    _LOGGER.debug("Sensor platform setup deferred to Step 7")
    # TODO Step 7: create one MeshCoreSensorEntity per configured channel
