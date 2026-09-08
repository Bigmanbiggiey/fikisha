"""Private object-storage abstraction (Phase 1 evidence-storage.md, ADR-013).

The application never depends on one storage provider and never exposes a bucket
URL to a client. Phase 2A ships:
  * ``PrivateStorage`` — the interface (put / stat / signed_url / open / delete),
  * ``LocalPrivateStorage`` — a filesystem backend for dev/test,
  * ``S3PrivateStorage`` — an interface stub (raises until wired in a later phase),
  * ``get_storage()`` — the resolver, driven by ``FIKISHA_STORAGE['BACKEND']``.

The evidence *workflow* (validation, EXIF strip, hashing, malware scan,
retention, access logging) is NOT built here — it arrives with the Evidence
module.
"""

from fikisha.storage.service import get_storage

__all__ = ("get_storage",)
