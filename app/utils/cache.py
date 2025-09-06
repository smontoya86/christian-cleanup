import json
import os
from typing import Any, Optional

import redis
from flask import current_app


def _get_redis_url() -> str:
    try:
        url = current_app.config.get("RQ_REDIS_URL") or current_app.config.get("REDIS_URL")
        if url:
            return url
    except RuntimeError:
        pass
    return os.environ.get("REDIS_URL") or os.environ.get("RQ_REDIS_URL", "redis://redis:6379/0")


def get_redis_client() -> Optional[redis.Redis]:
    try:
        client = redis.Redis.from_url(_get_redis_url(), decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def cache_set_json(key: str, value: Any, ttl_seconds: int = 60) -> None:
    client = get_redis_client()
    if not client:
        return
    try:
        client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception:
        pass


def cache_get_json(key: str) -> Optional[Any]:
    client = get_redis_client()
    if not client:
        return None
    try:
        data = client.get(key)
        if not data:
            return None
        return json.loads(data)
    except Exception:
        return None


def cache_delete(key: str) -> None:
    client = get_redis_client()
    if not client:
        return
    try:
        client.delete(key)
    except Exception:
        pass


