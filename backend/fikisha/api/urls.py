from __future__ import annotations

from django.conf import settings
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class ApiNotFoundView(APIView):
    """Catch-all so any unknown ``/api/v1/*`` path returns problem+json (not
    Django's HTML 404).
    """

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    def _not_found(self, *args: object, **kwargs: object) -> Response:
        raise NotFound(detail="No such API resource.", code="not_found")

    get = post = put = patch = delete = head = options = _not_found


from fikisha.observability.health import ApiHealthView  # noqa: E402

urlpatterns = [
    path("health/", ApiHealthView.as_view(), name="api-health"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("", include("fikisha.identity.api.urls")),
    # Phase 2B — identity & organisation domain.
    path("", include("fikisha.business.api.urls")),
    path("", include("fikisha.operators.api.urls")),
    path("", include("fikisha.groups.api.urls")),
    # Phase 2C — vehicles & verification.
    path("", include("fikisha.vehicles.api.urls")),
    path("", include("fikisha.verification.api.urls")),
    # Phase 2D — jobs & core coordination (Step 10 — API boundary).
    path("", include("fikisha.jobs.api.urls")),
    path("", include("fikisha.negotiation.api.urls")),
    path("", include("fikisha.incidents.api.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("docs/", SpectacularRedocView.as_view(url_name="v1:schema"), name="api-docs"),
    ]

# Must be last: everything else under /api/v1/ -> problem+json 404.
urlpatterns += [re_path(r"^.*$", ApiNotFoundView.as_view(), name="api-not-found")]
