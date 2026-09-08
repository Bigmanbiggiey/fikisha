from __future__ import annotations

import io

import pytest
from django.test import override_settings

from fikisha.storage.base import ObjectNotFound
from fikisha.storage.local import LocalPrivateStorage
from fikisha.storage.s3 import S3PrivateStorage
from fikisha.storage.service import get_storage, reset_storage_cache


@pytest.fixture
def local_storage(tmp_path: object) -> LocalPrivateStorage:
    return LocalPrivateStorage(root=str(tmp_path))


class TestLocalStorage:
    def test_put_stat_open_roundtrip(self, local_storage: LocalPrivateStorage) -> None:
        stored = local_storage.put(
            "verification/2026/01/abc.bin", b"hello", content_type="text/plain"
        )
        assert stored.size == 5
        assert stored.sha256 == ("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
        assert local_storage.exists("verification/2026/01/abc.bin")
        assert local_storage.stat("verification/2026/01/abc.bin").size == 5
        assert local_storage.open("verification/2026/01/abc.bin").read() == b"hello"

    def test_put_accepts_file_like(self, local_storage: LocalPrivateStorage) -> None:
        local_storage.put("k", io.BytesIO(b"streamed"))
        assert local_storage.open("k").read() == b"streamed"

    def test_missing_object_raises(self, local_storage: LocalPrivateStorage) -> None:
        with pytest.raises(ObjectNotFound):
            local_storage.stat("nope")

    def test_delete(self, local_storage: LocalPrivateStorage) -> None:
        local_storage.put("k", b"x")
        local_storage.delete("k")
        assert not local_storage.exists("k")

    def test_path_traversal_rejected(self, local_storage: LocalPrivateStorage) -> None:
        with pytest.raises(ValueError):
            local_storage.put("../../etc/passwd", b"x")

    def test_signed_url_is_not_a_bucket_url(self, local_storage: LocalPrivateStorage) -> None:
        local_storage.put("verification/2026/01/secret.bin", b"x")
        url = local_storage.signed_url("verification/2026/01/secret.bin")
        token = url.split("t=", 1)[1]
        # It's an API path with an opaque signed token — not a filesystem path,
        # not an http(s) bucket URL, and the key is not readable in the clear.
        assert url.startswith("/api/v1/storage/object?t=")
        assert "://" not in url
        assert str(local_storage.root) not in url
        assert "verification/2026/01/secret.bin" not in url
        # ...but the server can recover the key from the token.
        assert local_storage.resolve_signed(token) == "verification/2026/01/secret.bin"


class TestS3Stub:
    def test_s3_methods_raise_not_implemented(self) -> None:
        s3 = S3PrivateStorage()
        with pytest.raises(NotImplementedError):
            s3.put("k", b"x")
        with pytest.raises(NotImplementedError):
            s3.signed_url("k")


class TestResolver:
    def test_default_backend_is_local(self) -> None:
        reset_storage_cache()
        assert isinstance(get_storage(), LocalPrivateStorage)

    def test_resolver_honours_setting(self) -> None:
        reset_storage_cache()
        with override_settings(FIKISHA_STORAGE={**_s3_settings()}):
            reset_storage_cache()
            assert isinstance(get_storage(), S3PrivateStorage)
        reset_storage_cache()


def _s3_settings() -> dict:
    from django.conf import settings

    return {**settings.FIKISHA_STORAGE, "BACKEND": "s3"}
