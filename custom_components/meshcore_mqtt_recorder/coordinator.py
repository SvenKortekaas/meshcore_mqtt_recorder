"""MeshCore pipeline coordinator.

Ties the MQTT client, envelope parser, and decoder together.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

from .const import (
    _LOGGER,
    CONF_CHANNELS,
    CONF_IATA,
    CONF_WS_PATH,
    DEDUP_TTL_SECONDS,
    EVENT_MESSAGE_RECEIVED,
    MQTT_TOPIC_PATTERN,
)
from .decoder import MeshCoreChannelDecoder
from .dedup import HashDedupCache
from .envelope import EnvelopeParseError, parse_envelope
from .mqtt_client import MeshCoreMqttClient

if TYPE_CHECKING:
    from collections.abc import Callable

    import aiomqtt
    from homeassistant.core import HomeAssistant

    from .data import MeshCoreConfigEntry
    from .decoder import ChannelMessage
    from .envelope import Envelope


def _build_event_payload(msg: ChannelMessage, envelope: Envelope) -> dict[str, object]:
    return {
        "channel": msg.channel,
        "text": msg.text,
        "sender": msg.sender,
        "msg_id": msg.msg_id,
        "timestamp": envelope.timestamp,
        "observer": envelope.origin,
        "observer_id": envelope.origin_id,
        "snr": envelope.snr,
        "rssi": envelope.rssi,
        "packet_type": envelope.packet_type,
        "path_length": envelope.length,
    }


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
        self._listeners: dict[
            str, list[Callable[[ChannelMessage, Envelope], None]]
        ] = {}
        entry.async_on_unload(entry.add_update_listener(self._on_options_update))

    def async_start(self) -> None:
        """Spawn the MQTT background task tied to this config entry."""
        self.entry.async_create_background_task(
            self.hass,
            self._client.async_run(),
            name=f"meshcore_mqtt_{self.entry.entry_id}",
        )

    def add_listener(
        self,
        channel: str,
        callback: Callable[[ChannelMessage, Envelope], None],
    ) -> Callable[[], None]:
        """Register *callback* for decoded messages on *channel*.

        Returns an unsubscribe callable; call it in async_will_remove_from_hass.
        """
        self._listeners.setdefault(channel, []).append(callback)

        def _remove() -> None:
            with contextlib.suppress(KeyError, ValueError):
                self._listeners[channel].remove(callback)

        return _remove

    async def _on_options_update(
        self, _hass: HomeAssistant, entry: MeshCoreConfigEntry
    ) -> None:
        """Reload the config entry when options change.

        A full reload rebuilds coordinator, key store, and sensor entities atomically.
        Channel list changes are infrequent; the brief MQTT reconnect is acceptable.
        """
        _LOGGER.info(
            "meshcore mqtt: options updated — scheduling entry reload to"
            " rebuild sensor entities"
        )
        self.hass.async_create_task(
            self.hass.config_entries.async_reload(entry.entry_id)
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

        for cb in list(self._listeners.get(msg.channel, [])):
            try:
                cb(msg, envelope)
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "meshcore mqtt: listener error for channel #%s",
                    msg.channel,
                    exc_info=True,
                )

        self.hass.bus.async_fire(
            EVENT_MESSAGE_RECEIVED, _build_event_payload(msg, envelope)
        )
