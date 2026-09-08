from __future__ import annotations

from typing import BinaryIO

from django.conf import settings

from fikisha.storage.base import PrivateStorage, StoredObject


class S3PrivateStorage(PrivateStorage):
    """S3-compatible private storage — interface stub.

    Phase 2A does NOT wire production storage (Phase 2A brief §6, §26). This class
    exists so ``get_storage()`` has a real target and later phases implement the
    body with ``boto3`` against a private bucket (SSE + short-TTL pre-signed
    GETs, never a public URL). Calling any method now raises clearly.
    """

    def __init__(self) -> None:
        self._cfg = settings.FIKISHA_STORAGE["S3"]

    def _not_wired(self) -> NotImplementedError:
        return NotImplementedError(
            "S3PrivateStorage is a Phase 2A interface stub. Set STORAGE_BACKEND=local "
            "for development; the S3 backend is implemented alongside the Evidence module."
        )

    def put(
        self, key: str, data: BinaryIO | bytes, *, content_type: str = "application/octet-stream"
    ) -> StoredObject:
        raise self._not_wired()

    def stat(self, key: str) -> StoredObject:
        raise self._not_wired()

    def open(self, key: str) -> BinaryIO:
        raise self._not_wired()

    def signed_url(self, key: str, *, ttl_seconds: int | None = None) -> str:
        raise self._not_wired()

    def delete(self, key: str) -> None:
        raise self._not_wired()

    def exists(self, key: str) -> bool:
        raise self._not_wired()
