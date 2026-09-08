from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import BinaryIO

from django.conf import settings
from django.core import signing

from fikisha.storage.base import ObjectNotFound, PrivateStorage, StoredObject

_SALT = "fikisha.storage.local.v1"


class LocalPrivateStorage(PrivateStorage):
    """Filesystem-backed private storage for dev/test.

    Files live under a root that is **not** served by any web server. A
    "signed url" is a signed token the API would exchange for bytes — it is not
    a fetchable link and contains no filesystem path.
    """

    def __init__(self, root: str | Path | None = None, *, default_ttl: int | None = None) -> None:
        cfg = settings.FIKISHA_STORAGE
        self.root = Path(root or cfg["LOCAL_ROOT"]).resolve()
        self.default_ttl = default_ttl or cfg["SIGNED_URL_TTL_SECONDS"]
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        key = key.lstrip("/")
        target = (self.root / key).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError("path traversal detected in storage key")
        return target

    def put(
        self, key: str, data: BinaryIO | bytes, *, content_type: str = "application/octet-stream"
    ) -> StoredObject:
        payload = data if isinstance(data, bytes) else data.read()
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        return StoredObject(key=key, size=len(payload), content_type=content_type, sha256=digest)

    def stat(self, key: str) -> StoredObject:
        path = self._path(key)
        if not path.exists():
            raise ObjectNotFound(key)
        payload = path.read_bytes()
        return StoredObject(
            key=key,
            size=len(payload),
            content_type="application/octet-stream",
            sha256=hashlib.sha256(payload).hexdigest(),
        )

    def open(self, key: str) -> BinaryIO:
        path = self._path(key)
        if not path.exists():
            raise ObjectNotFound(key)
        return io.BytesIO(path.read_bytes())

    def signed_url(self, key: str, *, ttl_seconds: int | None = None) -> str:
        ttl = ttl_seconds or self.default_ttl
        token = signing.dumps({"key": key, "ttl": ttl}, salt=_SALT)
        # Points at an API route (to be implemented by the Evidence module).
        return f"/api/v1/storage/object?t={token}"

    def resolve_signed(self, token: str) -> str:
        data = signing.loads(token, salt=_SALT, max_age=self.default_ttl)
        return str(data["key"])

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()
