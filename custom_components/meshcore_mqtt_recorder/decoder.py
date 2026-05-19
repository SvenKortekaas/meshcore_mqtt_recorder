"""MeshCore channel decoder wrapper."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from meshcoredecoder import MeshCoreDecoder
from meshcoredecoder.crypto.key_manager import MeshCoreKeyStore
from meshcoredecoder.types.crypto import DecryptionOptions
from meshcoredecoder.types.enums import PayloadType

from .const import _LOGGER


@dataclass
class ChannelMessage:
    """A successfully decrypted hashtag channel message."""

    channel: str  # channel name without '#'
    text: str  # decrypted message text
    sender: str | None  # None when message is not in "name: text" format
    msg_id: str | None  # DecodedPacket.message_hash as packet UID
    raw_decoded: dict[str, object]  # full decrypted dict for forensics


def _channel_key_hex(name: str) -> str:
    """Derive the 16-byte AES-128 key hex for a hashtag channel name."""
    return hashlib.sha256(b"#" + name.encode()).digest()[:16].hex()


def _channel_hash(key_hex: str) -> str:
    """First byte of SHA256(key_bytes) as 2-char lowercase hex.

    Matches ChannelCrypto.calculate_channel_hash() in the meshcoredecoder library.
    Verified against v0.3.2 source: chrisdavis2110/meshcore-decoder-py.
    """
    return hashlib.sha256(bytes.fromhex(key_hex)).digest()[0:1].hex()


class MeshCoreChannelDecoder:
    """Wraps MeshCoreDecoder to decrypt hashtag channel GroupText packets."""

    def __init__(self, channels: list[str]) -> None:
        """Build keystore and channel-hash lookup map from channel names."""
        key_store = MeshCoreKeyStore()
        self._channel_hash_map: dict[str, str] = {}
        hex_keys: list[str] = []

        for name in channels:
            key_hex = _channel_key_hex(name)
            hex_keys.append(key_hex)
            ch = _channel_hash(key_hex)
            if ch in self._channel_hash_map:
                existing = self._channel_hash_map[ch]
                _LOGGER.warning(
                    "meshcore decoder: channel '#%s' shares channel_hash %s with '#%s';"
                    " messages may be misattributed. Rename one channel to resolve.",
                    name,
                    ch,
                    existing,
                )
            self._channel_hash_map[ch] = name

        if hex_keys:
            key_store.add_channel_secrets(hex_keys)

        self._options = DecryptionOptions(key_store=key_store)
        self._decoder_obj = MeshCoreDecoder()

    def decode_group_text(self, raw_hex: str) -> ChannelMessage | None:
        """Decode raw hex; return ChannelMessage on success, None otherwise."""
        try:
            packet = self._decoder_obj.decode(raw_hex, self._options)

            if not packet.is_valid or packet.payload_type != PayloadType.GroupText:
                return None

            payload_obj = packet.payload.get("decoded")
            if payload_obj is None:
                return None

            decrypted = getattr(payload_obj, "decrypted", None)
            if not isinstance(decrypted, dict):
                return None  # None or unexpected type → no successful decryption

            channel_hash = str(getattr(payload_obj, "channel_hash", "")).lower()
            channel_name = self._channel_hash_map.get(channel_hash)
            if channel_name is None:
                return None

            raw_message = decrypted.get("message", "")
            text = str(raw_message) if isinstance(raw_message, str) else ""
            raw_sender = decrypted.get("sender")
            sender: str | None = (
                str(raw_sender) if isinstance(raw_sender, str) else None
            )
            msg_id: str | None = packet.message_hash or None

            return ChannelMessage(
                channel=channel_name,
                text=text,
                sender=sender,
                msg_id=msg_id,
                raw_decoded=dict(decrypted),
            )
        except Exception:  # noqa: BLE001
            _LOGGER.debug(
                "meshcore decoder: exception decoding GroupText", exc_info=True
            )
            return None
