"""Health probes + the problem+json error contract."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


class TestHealth:
    def test_healthz_liveness(self, client: object) -> None:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_readyz_checks_dependencies(self, client: object) -> None:
        r = client.get("/readyz")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["checks"] == {"database": True, "cache": True}

    def test_api_health_endpoint(self, api: APIClient) -> None:
        r = api.get("/api/v1/health/")
        assert r.status_code == 200
        assert r.data["checks"]["database"] is True
        # No infrastructure detail leaks.
        raw = str(r.data)
        for leak in ("password", "5432", "localhost", "redis://", "SECRET"):
            assert leak not in raw


class TestErrorContract:
    def test_unknown_route_is_problem_json(self, api: APIClient) -> None:
        r = api.get("/api/v1/does-not-exist")
        assert r.status_code == 404
        assert r["content-type"] == "application/problem+json"
        assert set(r.data) >= {"type", "title", "status", "code", "detail", "request_id"}
        assert r.data["status"] == 404

    def test_malformed_json_body_is_problem_json(self, api: APIClient) -> None:
        r = api.post(
            "/api/v1/auth/otp/request",
            data='{"phone": "0700',  # deliberately broken JSON
            content_type="application/json",
        )
        assert r.status_code == 400
        assert r["content-type"] == "application/problem+json"
        assert r.data["status"] == 400
        assert r.data["code"]  # a stable machine code is present

    def test_missing_required_field_returns_field_errors(self, api: APIClient) -> None:
        r = api.post("/api/v1/auth/otp/request", {}, format="json")
        assert r.status_code == 400
        assert r["content-type"] == "application/problem+json"
        assert any(err["field"] == "phone" for err in r.data.get("errors", []))

    def test_invalid_uuid_in_path_is_not_a_server_error(self, api: APIClient) -> None:
        # An unparseable id on a <uuid:...> route resolves to the catch-all 404,
        # never a 500 or an HTML page.
        r = api.delete("/api/v1/me/sessions/not-a-uuid")
        assert r.status_code in {401, 404}
        assert r["content-type"] == "application/problem+json"

    def test_response_carries_request_id_header(self, api: APIClient) -> None:
        r = api.get("/api/v1/health/")
        assert r["X-Request-ID"]

    def test_incoming_request_id_is_echoed(self, api: APIClient) -> None:
        r = api.get("/api/v1/health/", HTTP_X_REQUEST_ID="test-req-12345678")
        assert r["X-Request-ID"] == "test-req-12345678"
