from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import BinaryIO


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    size: int
    content_type: str
    sha256: str


class ObjectNotFound(KeyError):
    pass


class PrivateStorage(abc.ABC):
    """Interface for private object storage. Implementations must never return a
    directly-fetchable public URL; ``signed_url`` returns a short-TTL,
    server-mediated handle only.
    """

    @abc.abstractmethod
    def put(
        self, key: str, data: BinaryIO | bytes, *, content_type: str = "application/octet-stream"
    ) -> StoredObject: ...

    @abc.abstractmethod
    def stat(self, key: str) -> StoredObject: ...

    @abc.abstractmethod
    def open(self, key: str) -> BinaryIO: ...

    @abc.abstractmethod
    def signed_url(self, key: str, *, ttl_seconds: int | None = None) -> str: ...

    @abc.abstractmethod
    def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    def exists(self, key: str) -> bool: ...
