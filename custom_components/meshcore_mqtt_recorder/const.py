"""Constants for MeshCore MQTT Recorder."""

from __future__ import annotations

import re
from logging import Logger, getLogger

_LOGGER: Logger = getLogger(__package__)

DOMAIN = "meshcore_mqtt_recorder"

# Custom config-entry keys; CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD
# are imported from homeassistant.const where needed
CONF_WS_PATH = "ws_path"
CONF_IATA = "iata"

# Options-flow key
CONF_CHANNELS = "channels"

# Broker defaults — the ONLY place these values are written; never hard-code elsewhere
DEFAULT_HOST = "subscriber.dutchmeshcore.nl"
DEFAULT_PORT = 443
DEFAULT_WS_PATH = "/mqtt"
DEFAULT_IATA = "AMS"

# MQTT topic template; format with iata= at subscribe time
MQTT_TOPIC_PATTERN = "meshcore/{iata}/+/packets"

# Deduplication cache TTL in seconds; 5 min covers full Dutch mesh propagation window
# (empirically up to 23 duplicate observations per packet)
DEDUP_TTL_SECONDS = 300

# JSONL history storage
STORAGE_SUBDIR = "meshcore_mqtt_recorder"
HISTORY_SENSOR_MESSAGES = 20  # last-N messages kept in sensor attributes
SERVICE_GET_HISTORY = "get_history"
HISTORY_DEFAULT_LIMIT = 100
HISTORY_MAX_LIMIT = 1000

# HA event name — fired on every successfully decrypted channel message
EVENT_MESSAGE_RECEIVED = "meshcore_message_received"

# Sensor entity naming
SENSOR_NAME_PREFIX = "meshcore"

# Validation — channel names: lowercase alphanumeric + interior hyphens only
# Pattern enforces: no leading/trailing hyphens, no consecutive hyphens
CHANNEL_NAME_REGEX: re.Pattern[str] = re.compile(
    r"^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9]))*$"
)
CHANNEL_NAME_MAX_LENGTH = 30

# Connection validation timeout in seconds
CONNECTION_TIMEOUT = 10

# MQTT reconnection backoff in seconds: doubles each attempt, capped at MAX
RECONNECT_DELAY_INITIAL = 5
RECONNECT_DELAY_MAX = 60

# Validation — IATA region codes: 2-4 uppercase letters
IATA_REGEX: re.Pattern[str] = re.compile(r"^[A-Z]{2,4}$")
