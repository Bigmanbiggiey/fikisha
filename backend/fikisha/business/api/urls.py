from __future__ import annotations

from django.urls import path

from fikisha.business.api import views

app_name = "business"

urlpatterns = [
    path("businesses", views.BusinessCollectionView.as_view(), name="collection"),
    path("businesses/<uuid:business_id>", views.BusinessDetailView.as_view(), name="detail"),
    path(
        "businesses/<uuid:business_id>/members",
        views.BusinessMemberCollectionView.as_view(),
        name="members",
    ),
    path(
        "businesses/<uuid:business_id>/members/<uuid:member_id>",
        views.BusinessMemberDetailView.as_view(),
        name="member-detail",
    ),
    path(
        "businesses/<uuid:business_id>/locations",
        views.BusinessLocationCollectionView.as_view(),
        name="locations",
    ),
    path(
        "businesses/<uuid:business_id>/locations/<uuid:location_id>",
        views.BusinessLocationDetailView.as_view(),
        name="location-detail",
    ),
]
