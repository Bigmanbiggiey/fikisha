from __future__ import annotations

from django.urls import path

from fikisha.inbox.api import views

app_name = "inbox"

urlpatterns = [
    path("messages", views.MessagesView.as_view(), name="messages"),
    path("messages/read", views.MessagesReadView.as_view(), name="messages-read"),
]
