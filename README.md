# MeshCore MQTT Recorder

A Home Assistant custom integration that subscribes to a MeshCore LoRa mesh network via
MQTT over WebSocket, decodes incoming packets, decrypts hashtag channel messages, and
records them as sensors, events, and a queryable history.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<!-- TODO: add screenshot before tagging, then uncomment below
![Dashboard screenshot](docs/screenshot.png)
-->

## What it does

- **MQTT subscription** — connects to a MeshCore observer broker (WebSocket over TLS) and
  subscribes to `meshcore/{IATA}/+/packets`, receiving raw packets from all observers in
  the configured region.
- **Packet decoding and deduplication** — decodes every packet with `meshcoredecoder`;
  deduplicates across the 20+ observer copies typically seen per packet using a 5-minute
  TTL cache.
- **Hashtag channel decryption** — derives AES-128 keys from channel names
  (`SHA256("#channel")`), decrypts `GroupText` payloads, and identifies the source channel.
- **Sensor entities** — creates one `sensor.meshcore_<channel>` per configured channel;
  state is the latest message preview, attributes carry the full message, sender, signal
  metadata, and a ring buffer of the last 20 messages.
- **HA events and Logbook** — fires a `meshcore_message_received` event per message and
  registers Logbook entries so the history renders in the HA Logbook UI.
- **Persistent JSONL history** — appends every decrypted message to
  `<config>/meshcore_mqtt_recorder/<channel>.jsonl`; queryable via the
  `meshcore_mqtt_recorder.get_history` service.

## Requirements

- Home Assistant 2024.10 or later (Python 3.12 is bundled — no separate install needed).
- An account on a MeshCore observer MQTT cluster. The Dutch cluster at
  [dutchmeshcore.nl](https://dutchmeshcore.nl) is the reference deployment; any compatible
  MeshCore observer broker should work.
- One or more hashtag channel names you want to decrypt (e.g. `general`, `aprs`).

## Installation

### HACS (recommended)

1. Open **HACS → Integrations**.
2. Click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/svenkortekaas/meshcore_mqtt_recorder` as type **Integration**.
4. Search for **MeshCore MQTT Recorder** and click **Download**.
5. Restart Home Assistant.

### Manual

1. Download the latest release ZIP from the
   [Releases](https://github.com/svenkortekaas/meshcore_mqtt_recorder/releases) page.
2. Unzip and copy the `meshcore_mqtt_recorder/` folder into your
   `config/custom_components/` directory.
3. Restart Home Assistant.

## Configuration

### Connection (config flow)

Go to **Settings → Devices & Services → Add Integration** and search for
**MeshCore MQTT Recorder**. The connection is validated against the broker before the
entry is saved.

| Field | Default | Description |
|---|---|---|
| Host | `subscriber.dutchmeshcore.nl` | MQTT broker hostname |
| Port | `443` | MQTT broker port |
| WebSocket path | `/mqtt` | WebSocket endpoint path |
| Username | — | Broker account username |
| Password | — | Broker account password |
| IATA region | `AMS` | 2–4 uppercase letters identifying the mesh region (e.g. `AMS`, `RTM`) |

### Channels (options flow)

After the integration is added, open its **Configure** dialog to set the channel list.
Enter hashtag channel names **without the `#` prefix**, one per line (e.g. `general`,
`aprs`). Keys are derived automatically from the channel name — no manual key entry
needed. Changes take effect immediately without reloading the integration.

## Entities, events, and Logbook

### Sensor entities

One sensor is created per configured channel:

- **Entity ID**: `sensor.meshcore_<channel>` (e.g. `sensor.meshcore_general`)
- **State**: latest message text, truncated to 255 characters.
- **Attributes**:

| Attribute | Description |
|---|---|
| `sender` | Display name of the sender node (`null` if not provided) |
| `timestamp` | ISO 8601 timestamp of the message |
| `msg_id` | Packet hash used as a unique message ID |
| `full_text` | Full untruncated message text |
| `last_messages` | Array of the last 20 messages (newest first), each with `message`, `sender`, `timestamp`, `msg_id` |
| `snr` | Signal-to-noise ratio reported by the observing node |
| `rssi` | Received signal strength (dBm) |
| `observer` | Display name of the observer node that received the packet |
| `path_length` | Number of hops the packet took through the mesh |

### Events

Every decrypted message fires a `meshcore_message_received` event on the HA event bus.
The event data includes:

```yaml
channel: general
message: Hello from the mesh
sender: NL-UTG-SV
timestamp: "2025-05-19T14:32:01+00:00"
msg_id: "a3f9..."
snr: "8.5"
rssi: "-87"
observer: NL-UTG-KRT-OBS01
path_length: 2
```

### Logbook

Each `meshcore_message_received` event is registered with HA's Logbook integration and
renders as a human-readable entry, for example:

> **MeshCore #general** — NL-UTG-SV: Hello from the mesh

## History service

The `meshcore_mqtt_recorder.get_history` service queries the on-disk JSONL archive. Call
it from **Developer Tools → Actions** or from automations.

```yaml
action: meshcore_mqtt_recorder.get_history
data:
  channel: general
  start: "2025-05-19T00:00:00+00:00"
  end: "2025-05-19T23:59:59+00:00"
  limit: 50
```

Results are returned in the service response, newest first. `start` and `end` are
optional; `limit` defaults to 100, maximum 1000.

## Lovelace example

A markdown card showing the latest message and signal details for a channel:

```yaml
type: markdown
content: >
  ## #general

  **{{ states('sensor.meshcore_general') }}**

  From: {{ state_attr('sensor.meshcore_general', 'sender') | default('unknown') }}

  At: {{ state_attr('sensor.meshcore_general', 'timestamp') }}

  Observer: {{ state_attr('sensor.meshcore_general', 'observer') }}
  · SNR {{ state_attr('sensor.meshcore_general', 'snr') }}
  · RSSI {{ state_attr('sensor.meshcore_general', 'rssi') }} dBm
```

Replace `general` with your channel name throughout.

## Limitations (v0.1.0)

- **Hashtag channels only.** Keys are derived from channel names. Pre-shared-key (PSK)
  channels with a manually configured hex key are not supported.
- **Single config entry.** Installing the integration twice in the same HA instance is
  not tested and not supported.
- **No JSONL rotation.** The history file grows without bound. Archive or truncate
  manually for high-traffic channels.
- **Channel-hash collision.** The decoder maps channels via the first byte of
  `SHA256(key)` — a 1-in-256 space shared across all configured channels. With 10
  channels the collision probability is ~16%; the last-registered channel wins. A warning
  appears in the HA log if a collision is detected at startup.
- **No custom timeline card.** The Lovelace example above is a markdown card workaround.
  A proper scrollable timeline card is planned for v0.2.

## License

MIT. See [LICENSE](LICENSE).

Bug reports and feature requests:
[github.com/svenkortekaas/meshcore_mqtt_recorder/issues](https://github.com/svenkortekaas/meshcore_mqtt_recorder/issues)
