"""Service registrations for MeshCore MQTT Recorder."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.core import SupportsResponse

from .const import (
    _LOGGER,
    CHANNEL_NAME_REGEX,
    CONF_CHANNELS,
    DOMAIN,
    HISTORY_DEFAULT_LIMIT,
    HISTORY_MAX_LIMIT,
    SERVICE_GET_HISTORY,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall


def _validate_channel(value: str) -> str:
    if not CHANNEL_NAME_REGEX.match(value):
        raise vol.Invalid(f"invalid channel name: {value!r}")
    return value


def _validate_iso(value: str) -> str:
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise vol.Invalid(f"invalid ISO 8601 timestamp: {value!r}") from exc
    return value


_GET_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Required("channel"): vol.All(str, _validate_channel),
        vol.Optional("start"): vol.All(str, _validate_iso),
        vol.Optional("end"): vol.All(str, _validate_iso),
        vol.Optional("limit", default=HISTORY_DEFAULT_LIMIT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=HISTORY_MAX_LIMIT)
        ),
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register domain services; no-op if already registered."""
    if hass.services.has_service(DOMAIN, SERVICE_GET_HISTORY):
        return

    async def _handle_get_history(call: ServiceCall) -> dict[str, Any]:
        channel: str = call.data["channel"]
        start: str | None = call.data.get("start")
        end: str | None = call.data.get("end")
        limit: int = call.data["limit"]

        # Find the entry whose channel list contains the requested channel.
        # v1 assumes a single config entry; multi-entry disambiguation is v0.2.
        entries = hass.config_entries.async_entries(DOMAIN)
        matched = [e for e in entries if channel in e.options.get(CONF_CHANNELS, [])]
        if len(matched) > 1:
            _LOGGER.warning(
                "meshcore services: channel #%s configured in %d entries;"
                " using first for get_history",
                channel,
                len(matched),
            )
        target = matched[0] if matched else (entries[0] if entries else None)
        if target is None:
            return {"messages": [], "count": 0, "channel": channel}

        messages = await target.runtime_data.coordinator.async_get_history(
            channel, start=start, end=end, limit=limit
        )
        return {"messages": messages, "count": len(messages), "channel": channel}

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_HISTORY,
        _handle_get_history,
        schema=_GET_HISTORY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Remove domain services when the last config entry is unloaded."""
    if len(hass.config_entries.async_entries(DOMAIN)) <= 1:
        hass.services.async_remove(DOMAIN, SERVICE_GET_HISTORY)
