"""Hash-based deduplication cache for MeshCore MQTT Recorder."""

from __future__ import annotations

import time

# Purge expired entries when cache exceeds this size to bound memory usage
_EVICTION_THRESHOLD = 5000


class HashDedupCache:
    """TTL cache keyed by envelope hash; eviction is lazy above threshold.

    Thread-unsafe by design — HA's event loop is single-threaded.
    """

    def __init__(self, ttl_seconds: int) -> None:
        """Initialise with the given TTL in seconds."""
        self._ttl = ttl_seconds
        self._seen: dict[str, float] = {}  # digest -> expiry (monotonic)

    def is_duplicate(self, digest: str) -> bool:
        """Return True if digest was seen within the TTL window (duplicate).

        Returns False if the digest is new, and records it for future checks.
        """
        now = time.monotonic()
        expiry = self._seen.get(digest)
        if expiry is not None and expiry > now:
            return True  # duplicate

        self._seen[digest] = now + self._ttl

        if len(self._seen) > _EVICTION_THRESHOLD:
            self._evict(now)

        return False  # new

    def _evict(self, now: float) -> None:
        """Remove all entries whose TTL has expired."""
        self._seen = {h: exp for h, exp in self._seen.items() if exp > now}
