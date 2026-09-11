"""Cross-cutting Step 10 checks: the RFC 9457 problem+json error contract
(brief §23) and a focused API STRIDE pass (brief §28) on top of the
per-endpoint authorization tests already covered elsewhere."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


class TestProblemJsonContract:
    def test_a_404_is_problem_json_with_a_request_id(
        self, client_for: Callable, business_actor: Any
    ) -> None:
        client = client_for(business_actor.user)
        r = client.get("/api/v1/jobs/00000000-0000-7000-8000-000000000000")
        assert r.status_code == 404
        assert r["content-type"] == "application/problem+json"
        for field in ("type", "title", "status", "code", "detail", "request_id"):
            assert field in r.data, field

    def test_a_403_is_problem_json_and_names_a_stable_code(
        self, client_for: Callable, other_user: Any, draft_job: Any
    ) -> None:
        client = client_for(other_user)
        r = client.get(f"/api/v1/jobs/{draft_job.id}")
        assert r.status_code == 403
        assert r["content-type"] == "application/problem+json"
        assert r.data["code"] == "authz.forbidden"

    def test_a_domain_guard_failure_is_422_problem_json(
        self, client_for: Callable, driver_actor: Any, make_assigned_job: Callable
    ) -> None:
        job = make_assigned_job()
        client = client_for(driver_actor.user)
        client.post(f"/api/v1/jobs/{job.id}/custody/arrive-pickup", format="json")
        r = client.post(
            f"/api/v1/jobs/{job.id}/custody/confirm-pickup/otp", {"code": "999999"}, format="json"
        )
        assert r.status_code == 422
        assert r["content-type"] == "application/problem+json"
        assert "request_id" in r.data

    def test_error_responses_never_include_a_stack_trace_or_db_detail(
        self, client_for: Callable, other_user: Any, draft_job: Any
    ) -> None:
        client = client_for(other_user)
        r = client.get(f"/api/v1/jobs/{draft_job.id}")
        dump = str(r.data).lower()
        for leak in ("traceback", "psycopg", "django.db", "select * from", " at 0x"):
            assert leak not in dump, leak

    def test_401_is_used_for_unauthenticated_not_403(self, api: APIClient) -> None:
        r = api.get("/api/v1/jobs")
        assert r.status_code == 401
        assert r["content-type"] == "application/problem+json"


class TestSpoofingResistance:
    def test_a_client_supplied_actor_id_in_the_body_is_ignored(
        self, client_for: Callable, business_actor: Any, other_user: Any, verified_business: Any
    ) -> None:
        """The server resolves the actor from the bearer token, never from
        request JSON — smuggling a different user's id into the payload does
        nothing (none of the serializers even declare such a field, so it is
        just dropped, but this pins that a job created this way is attributed
        to the *authenticated* caller, not the smuggled id)."""
        client = client_for(business_actor.user)
        payload = {
            "business_id": str(verified_business.id),
            "created_by": str(other_user.id),  # not a real field; must be ignored
            "actor_id": str(other_user.id),
            "pickup_location": {"address_text": "Depot"},
            "destination_location": {"address_text": "Shop"},
            "cargo": {"description": "cartons", "declared_value_kes": 1_200_000},
        }
        r = client.post("/api/v1/jobs", payload, format="json")
        assert r.status_code == 201, r.content

        from fikisha.jobs.models import Job

        job = Job.objects.get(id=r.data["id"])
        assert job.created_by_id == business_actor.user.id
        assert job.created_by_id != other_user.id

    def test_an_expired_or_garbage_bearer_token_is_401_not_500(self, api: APIClient) -> None:
        api.credentials(HTTP_AUTHORIZATION="Bearer garbage-not-a-real-token")
        r = api.get("/api/v1/jobs")
        assert r.status_code == 401
        assert r["content-type"] == "application/problem+json"


class TestElevationOfPrivilegeResistance:
    def test_an_ops_officer_cannot_escalate_a_privileged_admin_only_action(
        self,
        client_for: Callable,
        ops_officer: Any,
        delivered_job: Callable,
        complete_job: Callable,
    ) -> None:
        """Reprises the commission-adjustment / escalation boundary already
        proven per-endpoint elsewhere, as a single named cross-cutting check
        that an Ops Officer's admin-ish standing never reaches a
        Platform-Admin-only action."""
        job = delivered_job()
        complete_job(job)
        r = client_for(ops_officer).get(f"/api/v1/jobs/{job.id}/commission")
        assert r.status_code == 403


class TestInformationDisclosureAcrossOrganisations:
    def test_business_a_cannot_see_business_b_appear_in_a_search_by_id(
        self, client_for: Callable, business_actor: Any, make_user: Callable
    ) -> None:
        from fikisha.business.models import BusinessAccount

        stranger = make_user("+254700666001")
        other_biz = BusinessAccount.objects.create(owner_user=stranger, trading_name="Rival Co")
        r = client_for(business_actor.user).get("/api/v1/jobs")
        assert r.status_code == 200
        assert str(other_biz.id) not in str(r.data)
