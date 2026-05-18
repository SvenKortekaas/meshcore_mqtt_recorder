"""MQTT client lifecycle for MeshCore MQTT Recorder.

Step 3 — see CLAUDE.md §MQTT Client for full spec:
  - Library: aiomqtt (async wrapper around paho-mqtt)
  - Transport: WebSockets over TLS (transport="websockets")
  - Reconnection: exponential backoff, cap ~60 s
  - Topic pattern: meshcore/{IATA}/+/packets
"""
from __future__ import annotations


class MeshCoreMqttClient:
    """Manages the aiomqtt connection lifecycle for one config entry."""

    async def async_start(self) -> None:
        """Connect to the broker and begin listening for packets."""
        raise NotImplementedError("TODO Step 3")

    async def async_stop(self) -> None:
        """Disconnect from the broker and clean up resources."""
        raise NotImplementedError("TODO Step 3")
