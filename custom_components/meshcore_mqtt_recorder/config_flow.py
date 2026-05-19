"""Config flow for MeshCore MQTT Recorder."""

from __future__ import annotations

import asyncio
import ssl
from typing import Any

import aiomqtt
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers import selector

from .const import (
    _LOGGER,
    CHANNEL_NAME_MAX_LENGTH,
    CHANNEL_NAME_REGEX,
    CONF_CHANNELS,
    CONF_IATA,
    CONF_WS_PATH,
    CONNECTION_TIMEOUT,
    DEFAULT_HOST,
    DEFAULT_IATA,
    DEFAULT_PORT,
    DEFAULT_WS_PATH,
    DOMAIN,
    IATA_REGEX,
)


async def _validate_connection(data: dict[str, Any]) -> str:
    """Attempt a live broker connection; return '' on success or an error key."""
    tls_context = ssl.create_default_context()
    try:
        async with asyncio.timeout(CONNECTION_TIMEOUT):
            async with aiomqtt.Client(
                hostname=data[CONF_HOST],
                port=int(data[CONF_PORT]),
                transport="websockets",
                websocket_path=data[CONF_WS_PATH],
                tls_context=tls_context,
                username=data[CONF_USERNAME],
                password=data[CONF_PASSWORD],
            ):
                pass
    except TimeoutError:
        return "cannot_connect"
    except aiomqtt.MqttCodeError as exc:
        if exc.rc in (4, 5):  # CONNACK: bad credentials (4) or not authorised (5)
            return "invalid_auth"
        return "cannot_connect"
    except (OSError, aiomqtt.MqttError):
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error during MQTT connection validation")
        return "unknown"
    else:
        return ""


_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
        vol.Required(CONF_PORT, default=DEFAULT_PORT): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=65535, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(CONF_WS_PATH, default=DEFAULT_WS_PATH): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
        vol.Required(CONF_USERNAME): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_IATA, default=DEFAULT_IATA): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
    }
)


class MeshCoreMqttRecorderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for MeshCore MQTT Recorder."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle initial setup initiated by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            iata = str(user_input[CONF_IATA]).upper()
            user_input[CONF_IATA] = iata

            if not IATA_REGEX.match(iata):
                errors[CONF_IATA] = "invalid_iata"
            else:
                error_key = await _validate_connection(user_input)
                if error_key:
                    errors["base"] = error_key
                else:
                    unique_id = (
                        f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:{iata}"
                    )
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"MeshCore {iata}",
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_USER_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MeshCoreMqttRecorderOptionsFlow:
        """Return the options flow handler for this entry."""
        return MeshCoreMqttRecorderOptionsFlow(config_entry)


class MeshCoreMqttRecorderOptionsFlow(config_entries.OptionsFlow):
    """Options flow — manages the list of hashtag channels to monitor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the single options step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            channels: list[str] = user_input.get(CONF_CHANNELS, [])
            invalid = [
                ch
                for ch in channels
                if not CHANNEL_NAME_REGEX.match(ch) or len(ch) > CHANNEL_NAME_MAX_LENGTH
            ]
            if invalid:
                _LOGGER.warning("Invalid channel name(s) submitted: %s", invalid)
                errors[CONF_CHANNELS] = "invalid_channel_name"
            else:
                # TODO Step 6: hot-reload key store + subscriptions without entry reload
                return self.async_create_entry(title="", data=user_input)

        current_channels: list[str] = self._config_entry.options.get(CONF_CHANNELS, [])

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CHANNELS, default=current_channels
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(multiple=True)
                    ),
                }
            ),
            errors=errors,
        )
