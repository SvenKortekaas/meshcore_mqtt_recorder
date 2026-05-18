"""meshcoredecoder wrapper and AES key store management.

Step 5 — see CLAUDE.md §Packet Decoding and §Channel Key Derivation:
  - Library: meshcoredecoder (PyPI)
  - Key derivation: SHA256("#" + channel_name).digest()[:16]
  - Registration: MeshCoreKeyStore.add_channel_secrets([hex_key, ...])
  - Payload type filtering: PayloadType.GroupText only (never hard-code int values)
"""
from __future__ import annotations


class MeshCoreDecoder:
    """Wraps meshcoredecoder with key store management for configured channels."""

    def decode(self, raw_hex: str) -> object:
        """Decode a raw hex packet string.

        Returns the decoder result dict, or raises on decode failure.
        """
        raise NotImplementedError("TODO Step 5")
