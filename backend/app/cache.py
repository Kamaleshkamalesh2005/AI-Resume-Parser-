"""
Redis-backed cache for NLP results and model artefacts.

Falls back to an in-memory dict when Redis is not configured (e.g. tests).
Key format:  ``nlp:<sha256-hex>``
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_redis_client: Any | None = None
_fallback: Dict[str, str] = {}


def init_cache(redis_url: str) -> None:
    """Initialise the Redis connection (call once from the app factory)."""
    global _redis_client
    if not redis_url:
        logger.info("Redis URL empty – using in-memory fallback cache")
        return
    try:
        import redis as _redis_mod

        _redis_client = _redis_mod.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        _redis_client.ping()
        logger.info("Redis cache connected: %s", redis_url)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) – falling back to in-memory cache", exc)
        _redis_client = None


def _key(text: str, prefix: str = "nlp") -> str:
    return f"{prefix}:{hashlib.sha256(text.encode()).hexdigest()}"


def cache_get(text: str, prefix: str = "nlp") -> Optional[Dict[str, Any]]:
    """Return cached JSON dict for *text*, or ``None``."""
    k = _key(text, prefix)
    try:
        raw: str | None
        if _redis_client is not None:
            raw = _redis_client.get(k)
        else:
            raw = _fallback.get(k)
        if raw is not None:
            return json.loads(raw)
    except Exception:
        logger.debug("Cache read miss/error for key %s", k)
    return None


def cache_set(text: str, data: Dict[str, Any], ttl: int = 3600, prefix: str = "nlp") -> None:
    """Store *data* (JSON-serialisable dict) keyed on *text*."""
    k = _key(text, prefix)
    raw = json.dumps(data, default=str)
    try:
        if _redis_client is not None:
            _redis_client.setex(k, ttl, raw)
        else:
            _fallback[k] = raw
    except Exception:
        logger.debug("Cache write error for key %s", k)
