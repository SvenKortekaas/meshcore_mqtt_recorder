"""MeshCore pipeline coordinator.

Ties the MQTT client, envelope parser, and decoder together.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

from .const import (
    _LOGGER,
    CONF_IATA,
    CONF_WS_PATH,
    MQTT_TOPIC_PATTERN,
)
from .mqtt_client import MeshCoreMqttClient

if TYPE_CHECKING:
    import aiomqtt
    from homeassistant.core import HomeAssistant

    from .data import MeshCoreConfigEntry


class MeshCoreCoordinator:
    """Orchestrates the per-message pipeline for one config entry.

    Step 3 — owns MeshCoreMqttClient and the background task.
    Step 4 — add envelope parsing + dedup cache.
    Step 5 — add MeshCoreDecoder + key store.
    Steps 7-10 — fan out to sensor updates, events, logbook, JSONL storage.
    """

    def __init__(self, hass: HomeAssistant, entry: MeshCoreConfigEntry) -> None:
        """Initialise the coordinator and wire up the MQTT client."""
        self.hass = hass
        self.entry = entry
        topic = MQTT_TOPIC_PATTERN.format(iata=entry.data[CONF_IATA])
        self._client = MeshCoreMqttClient(
            host=entry.data[CONF_HOST],
            port=int(entry.data[CONF_PORT]),
            ws_path=entry.data[CONF_WS_PATH],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            topic=topic,
            on_message=self._handle_message,
        )

    def async_start(self) -> None:
        """Spawn the MQTT background task tied to this config entry."""
        self.entry.async_create_background_task(
            self.hass,
            self._client.async_run(),
            name=f"meshcore_mqtt_{self.entry.entry_id}",
        )

    async def _handle_message(self, message: aiomqtt.Message) -> None:
        """Step 3: log raw message. Step 4 adds JSON parsing and dedup."""
        payload = (
            bytes(message.payload)
            if isinstance(message.payload, (bytes, bytearray))
            else b""
        )
        _LOGGER.debug(
            "meshcore mqtt: topic=%s bytes=%d preview=%s",
            message.topic,
            len(payload),
            payload[:80].hex(),
        )
