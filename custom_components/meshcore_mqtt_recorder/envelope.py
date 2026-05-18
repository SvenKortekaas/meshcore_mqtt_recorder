"""MQTT envelope parsing and deduplication cache.

Step 4 — see CLAUDE.md §Envelope Parsing + Deduplication:
  - Parse the JSON envelope produced by Dutch observer nodes.
  - Deduplicate using the envelope hash field with a TTL cache.
  - Dedup check MUST happen BEFORE calling the decoder.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Envelope:
    """Represents one parsed MQTT envelope from an observer node."""

    # TODO Step 4: add fields matching CLAUDE.md §MQTT Payload Format
    # raw, origin, origin_id, timestamp, hash, SNR, RSSI, packet_type, direction


def parse_envelope(raw: bytes) -> Envelope:
    """Parse raw MQTT payload bytes into an Envelope.

    Raises ValueError on JSON parse error or missing required fields.
    """
    raise NotImplementedError("TODO Step 4")
