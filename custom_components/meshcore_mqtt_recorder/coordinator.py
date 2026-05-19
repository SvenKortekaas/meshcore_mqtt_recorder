"""MeshCore pipeline coordinator.

Ties the MQTT client, envelope parser, and decoder together.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

from .const import (
    _LOGGER,
    CONF_CHANNELS,
    CONF_IATA,
    CONF_WS_PATH,
    DEDUP_TTL_SECONDS,
    MQTT_TOPIC_PATTERN,
)
from .decoder import MeshCoreChannelDecoder
from .dedup import HashDedupCache
from .envelope import EnvelopeParseError, parse_envelope
from .mqtt_client import MeshCoreMqttClient

if TYPE_CHECKING:
    import aiomqtt
    from homeassistant.core import HomeAssistant

    from .data import MeshCoreConfigEntry


class MeshCoreCoordinator:
    """Orchestrates the per-message pipeline for one config entry.

    Step 3 — owns MeshCoreMqttClient and the background task.
    Step 4 — envelope parsing + dedup cache.
    Step 5 — MeshCoreChannelDecoder + hashtag key store.
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
        self._dedup = HashDedupCache(DEDUP_TTL_SECONDS)
        channels: list[str] = list(entry.options.get(CONF_CHANNELS, []))
        self._decoder: MeshCoreChannelDecoder | None = (
            MeshCoreChannelDecoder(channels) if channels else None
        )

    def async_start(self) -> None:
        """Spawn the MQTT background task tied to this config entry."""
        self.entry.async_create_background_task(
            self.hass,
            self._client.async_run(),
            name=f"meshcore_mqtt_{self.entry.entry_id}",
        )

    async def _handle_message(self, message: aiomqtt.Message) -> None:
        """Parse envelope, deduplicate, decode, and log channel messages."""
        payload = (
            bytes(message.payload)
            if isinstance(message.payload, (bytes, bytearray))
            else b""
        )

        try:
            envelope = parse_envelope(payload)
        except EnvelopeParseError as exc:
            _LOGGER.debug("meshcore mqtt: envelope parse error: %s", exc)
            return

        if self._dedup.is_duplicate(envelope.hash):
            return

        _LOGGER.debug(
            "meshcore mqtt: NEW origin=%s hash=%s type=%s snr=%s raw_len=%dB",
            envelope.origin,
            envelope.hash[:8],
            envelope.packet_type,
            envelope.snr,
            len(envelope.raw) // 2,
        )

        if self._decoder is None:
            return

        msg = self._decoder.decode_group_text(envelope.raw)
        if msg is None:
            return

        _LOGGER.info(
            "meshcore mqtt: CHANNEL #%s from %s text=%r (origin=%s, snr=%s)",
            msg.channel,
            msg.sender or "?",
            msg.text,
            envelope.origin,
            envelope.snr,
        )
