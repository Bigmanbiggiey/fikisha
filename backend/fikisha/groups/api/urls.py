from __future__ import annotations

from django.urls import path

from fikisha.groups.api import views

app_name = "groups"

urlpatterns = [
    path("groups", views.GroupCollectionView.as_view(), name="collection"),
    path("groups/<uuid:group_id>", views.GroupDetailView.as_view(), name="detail"),
    path(
        "groups/<uuid:group_id>/members",
        views.GroupMemberCollectionView.as_view(),
        name="members",
    ),
    path(
        "groups/<uuid:group_id>/members/<uuid:member_id>",
        views.GroupMemberDetailView.as_view(),
        name="member-detail",
    ),
    path("groups/<uuid:group_id>/bases", views.GroupBaseCollectionView.as_view(), name="bases"),
    path(
        "groups/<uuid:group_id>/bases/<uuid:membership_id>",
        views.GroupBaseDetailView.as_view(),
        name="base-detail",
    ),
]
