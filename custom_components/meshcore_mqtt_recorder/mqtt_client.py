"""MQTT client lifecycle for MeshCore MQTT Recorder."""

from __future__ import annotations

import asyncio
import ssl
from typing import TYPE_CHECKING

import aiomqtt

from .const import _LOGGER, RECONNECT_DELAY_INITIAL, RECONNECT_DELAY_MAX

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class MeshCoreMqttClient:
    """Manages the aiomqtt connection lifecycle for one config entry."""

    def __init__(
        self,
        host: str,
        port: int,
        ws_path: str,
        username: str,
        password: str,
        topic: str,
        on_message: Callable[[aiomqtt.Message], Awaitable[None]],
    ) -> None:
        """Initialise client parameters; TLS context created once and reused."""
        self._host = host
        self._port = port
        self._ws_path = ws_path
        self._username = username
        self._password = password
        self._topic = topic
        self._on_message = on_message
        self._tls_context = ssl.create_default_context()

    async def async_run(self) -> None:
        """Long-running reconnect loop; runs until CancelledError."""
        delay = RECONNECT_DELAY_INITIAL
        while True:
            try:
                async with aiomqtt.Client(
                    hostname=self._host,
                    port=self._port,
                    transport="websockets",
                    websocket_path=self._ws_path,
                    tls_context=self._tls_context,
                    username=self._username,
                    password=self._password,
                ) as client:
                    await client.subscribe(self._topic)
                    _LOGGER.info(
                        "meshcore mqtt: connected, subscribed to %s", self._topic
                    )
                    delay = RECONNECT_DELAY_INITIAL
                    async for message in client.messages:
                        await self._on_message(message)
            except asyncio.CancelledError:
                _LOGGER.info("meshcore mqtt: client stopped")
                raise
            except aiomqtt.MqttError as exc:
                _LOGGER.warning(
                    "meshcore mqtt: disconnected (%s) — reconnecting in %ds",
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_DELAY_MAX)
            except OSError as exc:
                _LOGGER.warning(
                    "meshcore mqtt: connection error (%s) — reconnecting in %ds",
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_DELAY_MAX)
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "meshcore mqtt: unexpected error — reconnecting in %ds", delay
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_DELAY_MAX)
