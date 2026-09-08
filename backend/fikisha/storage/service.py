from __future__ import annotations

from functools import lru_cache

from django.conf import settings

from fikisha.storage.base import PrivateStorage
from fikisha.storage.local import LocalPrivateStorage
from fikisha.storage.s3 import S3PrivateStorage

_BACKENDS = {
    "local": LocalPrivateStorage,
    "s3": S3PrivateStorage,
}


@lru_cache(maxsize=1)
def get_storage() -> PrivateStorage:
    backend = settings.FIKISHA_STORAGE["BACKEND"]
    try:
        return _BACKENDS[backend]()
    except KeyError as exc:  # pragma: no cover - config guard
        raise ValueError(
            f"Unknown FIKISHA_STORAGE backend {backend!r}; expected one of {sorted(_BACKENDS)}"
        ) from exc


def reset_storage_cache() -> None:
    """Test helper — drop the cached backend after changing settings."""
    get_storage.cache_clear()
