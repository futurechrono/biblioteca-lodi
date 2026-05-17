import time
from threading import Lock
from typing import Any, Callable

from .config import CACHE_TTL_SECONDS

_store: dict[str, tuple[float, Any]] = {}
_lock = Lock()


def get_or_set(key: str, producer: Callable[[], Any], ttl: int = CACHE_TTL_SECONDS) -> Any:
    now = time.time()
    with _lock:
        entry = _store.get(key)
        if entry and entry[0] > now:
            return entry[1]
    value = producer()
    with _lock:
        _store[key] = (now + ttl, value)
    return value


def clear() -> None:
    with _lock:
        _store.clear()
