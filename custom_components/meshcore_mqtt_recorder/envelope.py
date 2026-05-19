"""MQTT envelope parsing for MeshCore MQTT Recorder."""

from __future__ import annotations

import json
from dataclasses import dataclass


class EnvelopeParseError(ValueError):
    """Raised when an MQTT envelope cannot be parsed."""


@dataclass
class Envelope:
    """Represents one parsed MQTT envelope from an observer node."""

    # Required fields — EnvelopeParseError raised if any are absent
    raw: str
    origin: str
    origin_id: str
    timestamp: str
    hash: str
    # Optional fields — None when absent or unparseable
    snr: float | None = None
    rssi: float | None = None
    packet_type: str | None = None
    direction: str | None = None
    length: int | None = None  # JSON key "len"; renamed to avoid shadowing builtin
    payload_len: int | None = None
    route: str | None = None


def _coerce_float(value: object) -> float | None:
    """Coerce a JSON value to float, returning None on failure or empty string."""
    if value is None or value == "":
        return None
    if not isinstance(value, (str, int, float)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: object) -> int | None:
    """Coerce a JSON value to int, returning None on failure."""
    if value is None:
        return None
    if not isinstance(value, (str, int, float)):
        return None
    try:
        return int(value)
    except (ValueError, OverflowError):
        return None


def parse_envelope(raw: bytes) -> Envelope:
    """Parse raw MQTT payload bytes into an Envelope.

    Raises EnvelopeParseError on decode failure, non-object JSON, or
    missing required fields.
    """
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EnvelopeParseError(f"invalid JSON: {exc}") from exc

    if not isinstance(obj, dict):
        raise EnvelopeParseError("envelope is not a JSON object")

    data: dict[str, object] = obj

    try:
        env_raw = str(data["raw"])
        origin = str(data["origin"])
        origin_id = str(data["origin_id"])
        timestamp = str(data["timestamp"])
        env_hash = str(data["hash"])
    except KeyError as exc:
        raise EnvelopeParseError(f"missing required field: {exc}") from exc

    return Envelope(
        raw=env_raw,
        origin=origin,
        origin_id=origin_id,
        timestamp=timestamp,
        hash=env_hash,
        snr=_coerce_float(data.get("SNR")),
        rssi=_coerce_float(data.get("RSSI")),
        packet_type=str(data["packet_type"]) if "packet_type" in data else None,
        direction=str(data["direction"]) if "direction" in data else None,
        length=_coerce_int(data.get("len")),
        payload_len=_coerce_int(data.get("payload_len")),
        route=str(data["route"]) if "route" in data else None,
    )
