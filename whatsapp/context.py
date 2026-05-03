import json
import os
import redis

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    return _client


def get_context(number: str) -> dict | None:
    raw = _get_client().get(f"contexto:{number}")
    if raw is None:
        return None
    return json.loads(raw)


def set_context(number: str, data: dict) -> None:
    _get_client().set(f"contexto:{number}", json.dumps(data), ex=600)
