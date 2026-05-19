# MeshCore MQTT Recorder — Home Assistant Custom Integration

A HACS custom integration that subscribes to the Dutch MeshCore MQTT cluster (or any compatible MeshCore observer broker), decodes incoming packets, decrypts hashtag channel messages, and records them in Home Assistant as sensors + events + a queryable history.

## Architecture Decisions (LOCKED)

These are settled and verified against real Dutch mesh traffic via the discovery test script. Do not propose alternatives unless explicitly asked.

### MQTT Client
- **Library**: `aiomqtt` (async wrapper around paho-mqtt).
- **Transport**: WebSockets over TLS (`transport="websockets"`).
- **Default broker**: `wss://subscriber.dutchmeshcore.nl:443/mqtt` (host, port, and path all configurable — do not hard-code).
- **Reconnection**: must be automatic and resilient with exponential backoff (cap ~60 s).
- **TLS**: standard `ssl.create_default_context()`.
- **Windows asyncio note**: development on Windows requires `WindowsSelectorEventLoopPolicy` because paho-mqtt uses `add_reader`/`add_writer`, which the default `ProactorEventLoop` doesn't implement. Inside the HA runtime this is moot (HA uses Selector), but document it for any standalone test scripts.

### Topic Subscription
- **Pattern**: `meshcore/{IATA}/+/packets`
- **Default IATA**: `AMS` (configurable per-installation).
- **Subscribe target**: `meshcore/AMS/+/packets` — the `+` wildcard captures all observers in the region.
- The user's portal-side filter at dutchmeshcore.nl further narrows what we actually receive; we don't try to manage that.

### MQTT Payload Format (JSON envelope from observers)
Every payload is a UTF-8 JSON object produced by the Dutch observer nodes. Confirmed field schema:

| Field | Type | Use |
|---|---|---|
| `raw` | hex string | The raw MeshCore packet — passed to the decoder |
| `origin` | string | Observer node display name (e.g. `NL-UTG-KRT-OBS01`) |
| `origin_id` | hex string | Observer node public key |
| `timestamp` | ISO 8601 | Observation timestamp |
| `hash` | hex string | Packet hash — used for deduplication |
| `SNR`, `RSSI` | string/number | Signal quality |
| `packet_type` | string int | Envelope-level type hint (matches decoded `payloadType`) |
| `direction` | `rx` / `tx` | Observation direction |
| `len`, `payload_len`, `route` | — | Additional metadata, not used in v1 |

### Packet Decoding
- **Library**: `meshcoredecoder` (PyPI).
- **Decoder call**: `decoder.decode_to_json(raw_hex, DecryptionOptions(key_store=key_store))`.
- **Result schema** (confirmed): `{messageHash, routeType, payloadType, payloadVersion, pathLength, path, payload: {raw, decoded}, totalBytes, isValid, errors}`.
- **Payload type filtering**: use the library's `meshcoredecoder.types.enums.PayloadType` enum (`PayloadType.GroupText` for channel messages). Never hard-code integer values.

### Channel Key Derivation
- **Hashtag channels**: `key = SHA256("#" + channel_name).digest()[:16]` (16-byte AES-128 key, hex-encoded for the keystore).
- **Channel name validation**: alphanumeric, lowercase, hyphens allowed, no leading/trailing/double hyphens, max length 30.
- **Registration**: `MeshCoreKeyStore.add_channel_secrets([hex_key_1, hex_key_2, ...])` — plural, list-form.
- **Optional v2 feature**: support PSK (non-hashtag) channels via a user-supplied hex key map. Not in v1.

### Deduplication (mandatory)
Multiple observers see the same packet as it floods through the mesh — empirically 20+ observations per packet on the Dutch network. Deduplicate using the envelope's `hash` field:

- **Cache**: in-memory TTL dict keyed by `hash`.
- **TTL**: 5 minutes (long enough for full mesh propagation, short enough to bound memory).
- **Check position**: AFTER JSON parse, BEFORE calling the decoder. Decoding 20+ duplicates wastes CPU.
- **Implementation hint**: `collections.OrderedDict` with manual eviction, or `cachetools.TTLCache`. Either is fine; pick one in `const.py`.

### Per-Channel Entities
For each configured hashtag channel:

1. **Sensor entity** `sensor.meshcore_<channel_slug>`
   - State: short preview of latest message (truncated to 255 chars).
   - Attributes: `sender`, `timestamp` (ISO 8601), `msg_id`, `full_text`, `last_messages` (array of last 20), plus pass-through metadata `snr`, `rssi`, `observer`, `path_length`.

2. **HA event** `meshcore_message_received` fired on every decrypted channel message, payload includes the full message + envelope metadata + channel name.

3. **Logbook entry** registered via `homeassistant.components.logbook.async_describe_event` so events render human-readably in the Logbook UI.

### Long-Term History (the "Recorder" part)
- Append every decrypted channel message to `<config>/meshcore_mqtt_recorder/<channel_slug>.jsonl` (one JSON object per line, UTF-8, no rotation in v1).
- Each line contains: decoded message + envelope metadata + channel name + Unix epoch timestamp.
- Service `meshcore_mqtt_recorder.get_history` with params: `channel`, `start` (ISO timestamp, optional), `end` (optional), `limit` (default 100, max 1000).

### Config Flow (saved to `entry.data`, set once at install)
Fields:
- `host` (string, required, default `subscriber.dutchmeshcore.nl`)
- `port` (int, default `443`, range 1–65535)
- `ws_path` (string, default `/mqtt`)
- `username` (string, required)
- `password` (string, required, password-type)
- `iata` (string, default `AMS`, regex `^[A-Z]{2,4}$`)

**Connection MUST be validated in `async_step_user` before `async_create_entry`.** Spin up a real `aiomqtt.Client` with a short timeout (~10 s). On failure return `errors={"base": "cannot_connect"}` or `"invalid_auth"`.

### Options Flow (saved to `entry.options`, editable later)
- `channels` — list of hashtag channel names (without `#`), `TextSelector(multiple=True)`.
- Validate each entry matches the channel-name regex before saving.
- Channel list changes MUST hot-reload key store + subscriptions without integration reload (use `async_update_listener`).

## Per-Message Pipeline

For every MQTT message received on `meshcore/{IATA}/+/packets`:

1. Decode bytes → UTF-8 → `json.loads`. Skip and log on parse error.
2. Read `hash` from envelope. If present in the dedup cache → skip silently.
3. Add `hash` to dedup cache.
4. Extract `raw` hex from envelope.
5. Call `decoder.decode_to_json(raw_hex, decrypt_opts)`.
6. If `result["isValid"] is False` or errors present → log at DEBUG and skip.
7. If `result["payloadType"] != PayloadType.GroupText` → skip (not a channel message).
8. Determine which configured channel produced the successful decryption (the decoder result must indicate this — confirm field name during Step 3 and document here).
9. Extract plaintext message + sender + msg_id from `result["payload"]["decoded"]`.
10. Emit: sensor update → fire HA event → write JSONL line.

## Coding Standards

- **Python 3.12+** (matches current HA core).
- **Strict typing**: `mypy --strict` must pass. Type every function signature, return value, and class attribute.
- **Async**: never block the event loop. All IO async. Use `asyncio.to_thread` for unavoidable sync calls.
- **Logging**: `_LOGGER = logging.getLogger(__name__)`. `DEBUG` for verbose, `INFO` for lifecycle, `WARNING` for recoverable issues, `ERROR` for real problems. No `print`.
- **Constants**: all config keys, event names, payload-type values via enum import, dedup TTL, etc. live in `const.py`. No string literals scattered in code.
- **i18n**: all user-facing strings via `strings.json` + `translations/en.json` + `translations/nl.json`.
- **Tests**: pytest with `pytest-homeassistant-custom-component`. Aim for >80% coverage on core logic (envelope parsing, dedup cache, decoder integration, config flow validation).

## Dependencies

In `pyproject.toml` and `manifest.json`:

- `aiomqtt` (latest stable, websockets transport)
- `meshcoredecoder` (Python MeshCore decoder; pulls `cryptography`, `pycryptodome`)

No other runtime dependencies in v1.

## Build Sequence

Build in this order. Each step must be working, tested, and committed before starting the next.

1. **Scaffold** from Ludeeus's `integration_blueprint` template, renamed to `meshcore_mqtt_recorder`. Strip what we don't need.
2. **Config flow** — host/port/ws_path/username/password/iata fields + real connection validation.
3. **MQTT client** — connects on setup, subscribes to `meshcore/{IATA}/+/packets`, logs every parsed envelope to HA log at DEBUG. No decoding yet.
4. **Envelope parsing + deduplication** — JSON parse, hash-based dedup cache with TTL.
5. **Decoder integration** — call `decode_to_json`, log decoded results at DEBUG. Identify the field that maps a decrypted GroupText back to its channel name; document the finding in this file.
6. **Options flow** — channels list + dynamic key store updates + dynamic subscription is unchanged (topic doesn't depend on channels).
7. **Sensor entities** per channel (state + attributes).
8. **HA events** fired on each channel message.
9. **Logbook integration**.
10. **JSONL persistence** (the recorder core).
11. **`get_history` service**.
12. **README + HACS metadata + GitHub release workflow**.

After each step: tests pass → commit → push → advance.

## Workflow Rules (READ EVERY SESSION)

### Plan-First, Always
Before editing any file:
1. State which Build Sequence step we are on.
2. List the files you intend to create or modify.
3. Describe the change in 3–5 sentences.
4. **Wait for explicit approval** before writing.

If you find yourself reaching for an edit tool without an approved plan in the current turn — stop.

### Scope Discipline
- Only touch files relevant to the current step.
- Do not refactor "while you're in there" — propose refactors as a separate task.
- Do not invent features not listed in this document. Ask first.

### Things to Never Do
- Never use Home Assistant's built-in MQTT integration as a dependency — we use our own client.
- Never use `paho-mqtt` directly — use `aiomqtt`.
- Never use blocking sync IO on the event loop (no `requests`, no `time.sleep`, no bare `open()`).
- Never skip connection validation in the config flow.
- Never commit secrets, `.env` files, or local broker test credentials.
- Never modify `manifest.json` version field manually — the release workflow handles it.
- Never hard-code the broker hostname, port, websocket path, or IATA region anywhere outside of defaults in `const.py`.
- Never hard-code MeshCore payload type integers — always use `meshcoredecoder.types.enums.PayloadType`.
- Never write code that processes a packet without first checking the dedup cache.

### Commit Conventions
- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
- One logical change per commit.
- Reference the Build Sequence step in the commit body, e.g.: `Step 4: envelope parsing + dedup cache`.

## Project Structure

```
meshcore_mqtt_recorder/
├── .github/workflows/release.yml
├── custom_components/meshcore_mqtt_recorder/
│   ├── __init__.py
│   ├── manifest.json
│   ├── const.py
│   ├── config_flow.py
│   ├── mqtt_client.py        # aiomqtt connection lifecycle
│   ├── envelope.py           # JSON envelope parsing + dedup cache
│   ├── decoder.py            # meshcoredecoder wrapper + key store
│   ├── coordinator.py        # ties pipeline pieces together
│   ├── sensor.py
│   ├── logbook.py
│   ├── storage.py            # JSONL writer + history reader
│   ├── services.py
│   ├── services.yaml
│   ├── strings.json
│   └── translations/
│       ├── en.json
│       └── nl.json
├── tests/
├── CLAUDE.md
├── hacs.json
├── README.md
├── pyproject.toml
└── requirements.txt
```

## Repository

- **License**: MIT.
- **HACS-compatible**: `hacs.json` at repo root, integration code under `custom_components/meshcore_mqtt_recorder/`.
- **Release**: GitHub Action publishes on tag push (`v*.*.*`); `manifest.json` version bumped by the action, not by hand.
- **Multi-machine**: this repo is the source of truth. Pull before starting a session, push when leaving.

## Discovery Findings (frozen reference)

These were validated against real Dutch mesh traffic on 2026-05-18 and inform the architecture above. Do not change without re-validating.

- 30/30 packets captured, parsed, and decoded without errors.
- Observed `payloadType` distribution: type 0 (~77%), type 2 (~20%), invalid/empty (~3%).
- Same packet `messageHash` observed up to 23 times across different observers within seconds → mandatory dedup.
- No channel text messages decrypted in the sample window — to be verified during Step 5.

### Step 5 additions — validated 2026-05-19 against meshcoredecoder v0.3.2 source (chrisdavis2110/meshcore-decoder-py)

**Use `decode()`, not `decode_to_json()`.**
`decode_to_json()` serialises `GroupTextPayload` via `BasePayload.to_dict()` which only
emits `{type, version, isValid}`. `channel_hash` and `decrypted` content are absent from
the JSON string. Use `MeshCoreDecoder().decode(raw_hex, options) -> DecodedPacket`.

**Channel identification field:**
`packet.payload["decoded"].channel_hash` — 2-char lowercase hex (e.g. `"a3"`),
computed as first byte of `SHA256(secret_key_bytes)`. Build a reverse map at startup:
`_channel_hash_map: dict[str, str]` — channel_hash → channel_name.
Hash collision probability is ~16% among 10 channels (birthday paradox on 1 byte);
warn on collision at construction time, last-registered channel wins.

**Channel hash formula** (matches `ChannelCrypto.calculate_channel_hash()`):
`hashlib.sha256(bytes.fromhex(key_hex)).digest()[0:1].hex()`

**Failed decryption:** `GroupTextPayload.is_valid` is `True` even on failed decryption
(set at structure-parse time, not after crypto). Success check: `payload_obj.decrypted is not None`.

**Decrypted GroupText fields:** `{"timestamp": int, "flags": int, "sender": str|None, "message": str}`.
No `msg_id` — use `DecodedPacket.message_hash` as packet UID.

**Import paths (installed package):**
```
from meshcoredecoder import MeshCoreDecoder
from meshcoredecoder.crypto.key_manager import MeshCoreKeyStore
from meshcoredecoder.types.crypto import DecryptionOptions
from meshcoredecoder.types.enums import PayloadType
```