"""Sensor platform for MeshCore MQTT Recorder — one entity per hashtag channel."""

from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity

from .const import CONF_CHANNELS, HISTORY_SENSOR_MESSAGES

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import MeshCoreConfigEntry
    from .decoder import ChannelMessage
    from .envelope import Envelope

_LOGGER = logging.getLogger(__name__)

_HA_STATE_MAX = 255


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MeshCoreConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one MeshCoreChannelSensor per configured channel."""
    channels: list[str] = list(entry.options.get(CONF_CHANNELS, []))
    if not channels:
        return
    async_add_entities([MeshCoreChannelSensor(entry, ch) for ch in channels])


class MeshCoreChannelSensor(SensorEntity):
    """Tracks the latest decrypted message on one hashtag channel.

    State: message preview truncated to 255 chars (HA state limit).
    None (unknown) until the first message arrives.
    Attributes: sender, timestamp, msg_id, full_text, snr, rssi, observer,
                path_length, last_messages (ring buffer of last 20).
    """

    _attr_should_poll = False
    _attr_icon = "mdi:message-text"

    def __init__(self, entry: MeshCoreConfigEntry, channel: str) -> None:
        """Initialise sensor for *channel* under *entry*."""
        self._channel = channel
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{channel}"
        self._attr_name = f"MeshCore {channel}"
        self._attr_native_value: str | None = None
        self._attr_extra_state_attributes: dict[str, object] = {}
        self._last_messages: deque[dict[str, object]] = deque(
            maxlen=HISTORY_SENSOR_MESSAGES
        )
        self._unsubscribe: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Register message listener with coordinator."""
        coordinator = self._entry.runtime_data.coordinator
        self._unsubscribe = coordinator.add_listener(self._channel, self._on_message)

    async def async_will_remove_from_hass(self) -> None:
        """Deregister message listener."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _on_message(self, msg: ChannelMessage, envelope: Envelope) -> None:
        """Update state and attributes atomically on each decoded message."""
        last_entry: dict[str, object] = {
            "timestamp": envelope.timestamp,
            "sender": msg.sender,
            "text": msg.text,
            "snr": envelope.snr,
            "rssi": envelope.rssi,
            "observer": envelope.origin,
        }
        self._last_messages.append(last_entry)
        self._attr_native_value = msg.text[:_HA_STATE_MAX]
        self._attr_extra_state_attributes = {
            "sender": msg.sender,
            "timestamp": envelope.timestamp,
            "msg_id": msg.msg_id,
            "full_text": msg.text,
            "snr": envelope.snr,
            "rssi": envelope.rssi,
            "observer": envelope.origin,
            "path_length": envelope.length,
            "last_messages": list(self._last_messages),
        }
        self.async_write_ha_state()
