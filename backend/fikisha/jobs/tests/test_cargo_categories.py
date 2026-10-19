"""Cargo categories that sort themselves (assessment 2026-10-19 part 6, D-5)."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import pytest

from fikisha.admin_console import services as admin_services
from fikisha.jobs import cargo_categories
from fikisha.jobs.models import Job

pytestmark = pytest.mark.django_db


def _payload(business_id: str, description: str, category_code: str = "") -> dict[str, Any]:
    return {
        "business_id": business_id,
        "pickup_location": {"address_text": "Depot"},
        "destination_location": {"address_text": "Shop"},
        "cargo": {
            "description": description,
            "category_code": category_code,
            "declared_value_kes": 1_000_000,
        },
    }


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("20 bags of cement", "CONSTRUCTION_MATERIALS"),
        ("Magunia 10 ya mahindi", "AGRICULTURE_PRODUCE"),
        ("Two laptops and a printer", "ELECTRONICS"),
        ("Cooking oil, 20 litres", "FOOD_BEVERAGE"),  # the phrase, not "oil"
        ("Mafuta ya kupikia", "FOOD_BEVERAGE"),
        ("Dizeli lita 200", "LIQUIDS_BULK"),
        ("5 goats", "LIVESTOCK"),
        ("A blue widget", None),
    ],
)
def test_the_description_suggests_a_category(description: str, expected: str | None) -> None:
    assert cargo_categories.suggest(description) == expected


class TestJobCreation:
    def test_no_category_picked_means_the_keywords_choose_and_set_latent_risk(
        self, client_for: Callable, business_actor: Any, verified_business: Any
    ) -> None:
        r = client_for(business_actor.user).post(
            "/api/v1/jobs", _payload(str(verified_business.id), "3 television sets"), format="json"
        )
        assert r.status_code == 201, r.content
        job = Job.objects.select_related("cargo").get(id=r.data["id"])
        assert job.cargo.category_code == "ELECTRONICS"
        assert job.cargo.category_auto is True
        # Electronics is a latent-risk category: the longer dispute window (F-6).
        assert job.latent_risk_cargo is True

    def test_a_picked_category_is_kept_and_not_marked_automatic(
        self, client_for: Callable, business_actor: Any, verified_business: Any
    ) -> None:
        r = client_for(business_actor.user).post(
            "/api/v1/jobs",
            _payload(str(verified_business.id), "3 television sets", "general"),
            format="json",
        )
        assert r.status_code == 201, r.content
        job = Job.objects.select_related("cargo").get(id=r.data["id"])
        assert (job.cargo.category_code, job.cargo.category_auto) == ("GENERAL", False)
        assert job.latent_risk_cargo is False

    def test_an_unknown_category_is_refused(
        self, client_for: Callable, business_actor: Any, verified_business: Any
    ) -> None:
        r = client_for(business_actor.user).post(
            "/api/v1/jobs",
            _payload(str(verified_business.id), "boxes", "SPACESHIPS"),
            format="json",
        )
        assert r.status_code == 422
        assert r.data["code"] == "unknown_cargo_category"

    def test_the_catalogue_and_suggest_endpoints(
        self, client_for: Callable, business_actor: Any, api: Any
    ) -> None:
        client = client_for(business_actor.user)
        cats = client.get("/api/v1/jobs/cargo-categories").data["data"]
        assert {"code": "ELECTRONICS", "latent_risk": True} in cats
        assert cats[-1]["code"] == "OTHER"
        r = client.get("/api/v1/jobs/cargo-categories/suggest", {"description": "bags of cement"})
        assert r.data == {"code": "CONSTRUCTION_MATERIALS"}
        assert api.get("/api/v1/jobs/cargo-categories").status_code == 401


class TestTeachingTheMatcher:
    @pytest.fixture
    def stepped_up(self, admin_actor: Any) -> Any:
        return dataclasses.replace(admin_actor, is_step_up_fresh=True)

    def test_an_unplaced_description_is_listed_until_an_admin_adds_a_keyword(
        self,
        client_for: Callable,
        business_actor: Any,
        verified_business: Any,
        stepped_up: Any,
    ) -> None:
        client = client_for(business_actor.user)
        for _ in range(2):
            client.post(
                "/api/v1/jobs",
                _payload(str(verified_business.id), "Mitungi ya gesi"),
                format="json",
            )
        job = Job.objects.select_related("cargo").latest("created_at")
        assert (job.cargo.category_code, job.cargo.category_auto) == ("OTHER", True)

        rows = admin_services.uncategorised_cargo(actor=stepped_up)
        assert rows[0]["description"] == "Mitungi ya gesi"
        assert rows[0]["count"] == 2

        # A keyword belongs to one category: "jiko" is already an appliance word.
        with pytest.raises(admin_services.InvalidConfigChange):
            admin_services.add_cargo_keyword(
                actor=stepped_up,
                category_code="LIQUIDS_BULK",
                keyword="jiko",
                rationale="Gas cylinders are bulk fuel",
            )
        admin_services.add_cargo_keyword(
            actor=stepped_up,
            category_code="LIQUIDS_BULK",
            keyword="Gesi",
            rationale="Gas cylinders are bulk fuel",
        )
        assert cargo_categories.suggest("Mtungi wa gesi") == "LIQUIDS_BULK"
        assert admin_services.uncategorised_cargo(actor=stepped_up) == []
        # The jobs already created keep their category.
        job.cargo.refresh_from_db()
        assert job.cargo.category_code == "OTHER"

    def test_an_admin_adds_a_category_before_other(self, stepped_up: Any) -> None:
        admin_services.add_cargo_category(
            actor=stepped_up,
            code="medical_supplies",
            keywords=["Syringes", "dawa"],
            rationale="Pharmacies in Kitengela",
        )
        assert cargo_categories.categories()[-2:] == ["MEDICAL_SUPPLIES", "OTHER"]
        assert cargo_categories.suggest("Box of syringes") == "MEDICAL_SUPPLIES"
        with pytest.raises(admin_services.InvalidConfigChange):
            admin_services.add_cargo_category(
                actor=stepped_up, code="MEDICAL_SUPPLIES", keywords=[], rationale="again, again"
            )

    def test_teaching_needs_a_platform_admin_with_a_fresh_step_up(
        self, admin_actor: Any, client_for: Callable, ops_officer: Any
    ) -> None:
        from fikisha.identity.authz.step_up import StepUpRequired

        with pytest.raises(StepUpRequired):  # no fresh authenticator code
            admin_services.add_cargo_keyword(
                actor=admin_actor,
                category_code="ELECTRONICS",
                keyword="radio",
                rationale="Radios are electronics",
            )
        r = client_for(ops_officer).post(
            "/api/v1/admin/cargo-categories/keywords",
            {
                "category_code": "ELECTRONICS",
                "keyword": "radio",
                "rationale": "Radios are electronics",
            },
            format="json",
        )
        assert r.status_code == 403
        assert (
            client_for(ops_officer).get("/api/v1/admin/cargo-categories/uncategorised").status_code
            == 403
        )
