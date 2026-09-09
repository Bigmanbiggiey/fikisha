"""Evidence store / stream / access log (Phase 2C §15, §28)."""

from __future__ import annotations

from typing import Any

import pytest

from fikisha.evidence import services
from fikisha.evidence.models import EvidenceAccessLog, EvidenceObject, PiiClass
from fikisha.evidence.services import EvidenceValidationError

pytestmark = pytest.mark.django_db


def test_store_computes_sha256_and_metadata() -> None:
    obj = services.store(
        data=b"hello-doc",
        content_type="image/png",
        purpose="VERIFICATION_DOC",
        pii_class=PiiClass.HIGH,
    )
    assert isinstance(obj, EvidenceObject)
    assert obj.size_bytes == len(b"hello-doc")
    assert len(obj.sha256) == 64
    assert obj.storage_key.startswith("evidence/verification_doc/")


def test_type_allowlist_is_enforced() -> None:
    with pytest.raises(EvidenceValidationError):
        services.store(
            data=b"x", content_type="application/x-msdownload", purpose="VERIFICATION_DOC"
        )


def test_size_cap_is_enforced() -> None:
    with pytest.raises(EvidenceValidationError):
        services.store(
            data=b"0" * (11 * 1024 * 1024),
            content_type="image/jpeg",
            purpose="VEHICLE_PHOTO",
        )


def test_empty_upload_rejected() -> None:
    with pytest.raises(EvidenceValidationError):
        services.store(data=b"", content_type="image/jpeg", purpose="VEHICLE_PHOTO")


def test_open_stream_logs_high_pii_access(user: Any) -> None:
    obj = services.store(
        data=b"id-scan",
        content_type="image/jpeg",
        purpose="VERIFICATION_DOC",
        pii_class=PiiClass.HIGH,
    )
    payload, ctype = services.open_stream(
        obj, actor_user=user, actor_role="OPERATIONS_OFFICER", reason="review"
    )
    assert payload == b"id-scan"
    assert ctype == "image/jpeg"
    log = EvidenceAccessLog.objects.get(evidence_object=obj)
    assert log.accessed_by_id == user.id
    assert log.reason == "review"


def test_open_stream_medium_pii_is_not_logged(user: Any) -> None:
    obj = services.store(
        data=b"photo",
        content_type="image/jpeg",
        purpose="VEHICLE_PHOTO",
        pii_class=PiiClass.MEDIUM,
    )
    services.open_stream(obj, actor_user=user)
    assert EvidenceAccessLog.objects.filter(evidence_object=obj).count() == 0
