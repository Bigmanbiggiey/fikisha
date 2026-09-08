"""Auth + foundation API views.

No business-domain endpoints. The demo endpoint proves the audit + outbox
atomicity path and is DEBUG + feature-flag gated.
"""

from __future__ import annotations

from typing import Any, cast

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from fikisha.audit import services as audit
from fikisha.common.exceptions import AuthorizationError
from fikisha.identity.api.serializers import (
    MeSerializer,
    MeUpdateSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    SessionSerializer,
)
from fikisha.identity.authz.permissions import ActionPermission
from fikisha.identity.models import AuthSession, User
from fikisha.identity.services import auth as auth_service
from fikisha.identity.services import otp as otp_service
from fikisha.outbox.services import emit
from fikisha.platform_config import services as config


def _user(request: Request) -> User:
    """The authenticated ``User`` on views guarded by ``ActionPermission``/``IsAuthenticated``."""
    return cast("User", request.user)


def _client_ip(request: Request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _set_refresh_cookie(response: Response, raw: str, expires_at: Any) -> None:
    cfg = settings.AUTH_CONFIG
    response.set_cookie(
        cfg["REFRESH_COOKIE_NAME"],
        raw,
        expires=expires_at,
        secure=cfg["COOKIE_SECURE"],
        httponly=True,
        samesite=cfg["COOKIE_SAMESITE"],
        path="/api/v1/auth/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(settings.AUTH_CONFIG["REFRESH_COOKIE_NAME"], path="/api/v1/auth/")


class OtpRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=OtpRequestSerializer,
        responses={202: OpenApiResponse(description="Challenge created")},
    )
    def post(self, request: Request) -> Response:
        serializer = OtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = otp_service.request_otp(
            phone=serializer.validated_data["phone"],
            purpose=serializer.validated_data["purpose"],
            request_ip=_client_ip(request),
        )
        body: dict[str, Any] = {"challenge_id": result.challenge_id}
        if result.dev_code is not None:
            body["dev_code"] = result.dev_code  # DEV/TEST ONLY (OTP_DEV_EXPOSE)
        return Response(body, status=status.HTTP_202_ACCEPTED)


class OtpVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=OtpVerifySerializer, responses={200: OpenApiResponse(description="Session issued")}
    )
    def post(self, request: Request) -> Response:
        serializer = OtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = otp_service.verify_otp(
            challenge_id=str(serializer.validated_data["challenge_id"]),
            code=serializer.validated_data["code"],
            request_ip=_client_ip(request),
        )
        issued = auth_service.start_session(
            user=user,
            device_label=request.data.get("device_label", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            ip=_client_ip(request),
        )
        response = Response(
            {
                "access_token": issued.access_token,
                "access_expires_in": issued.access_expires_in,
                "user": MeSerializer(user).data,
            }
        )
        _set_refresh_cookie(response, issued.refresh_token, issued.refresh_expires_at)
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiResponse(description="New access token")})
    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.AUTH_CONFIG["REFRESH_COOKIE_NAME"], "")
        issued = auth_service.refresh(raw_refresh=raw, ip=_client_ip(request))
        response = Response(
            {"access_token": issued.access_token, "access_expires_in": issued.access_expires_in}
        )
        _set_refresh_cookie(response, issued.refresh_token, issued.refresh_expires_at)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: OpenApiResponse(description="Logged out")})
    def post(self, request: Request) -> Response:
        session = request.auth
        if isinstance(session, AuthSession):
            auth_service.logout(session=session, ip=_client_ip(request))
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class MeView(APIView):
    permission_classes = [ActionPermission]
    required_action = "auth.me.read"

    @extend_schema(responses=MeSerializer)
    def get(self, request: Request) -> Response:
        return Response(MeSerializer(request.user).data)

    @extend_schema(request=MeUpdateSerializer, responses=MeSerializer)
    def patch(self, request: Request) -> Response:
        user = _user(request)
        serializer = MeUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        before = {"display_name": user.display_name, "locale": user.locale}
        with transaction.atomic():
            serializer.save()
            audit.record(
                actor=user,
                action="user.profile.updated",
                entity_type="user",
                entity_id=user.id,
                before=before,
                after=serializer.data,
            )
        return Response(MeSerializer(user).data)


class SessionListView(APIView):
    permission_classes = [ActionPermission]
    required_action = "auth.session.list"

    @extend_schema(responses=SessionSerializer(many=True))
    def get(self, request: Request) -> Response:
        qs = AuthSession.objects.filter(user=_user(request)).order_by("-last_seen_at")
        current_id = getattr(request.auth, "id", None)
        data = SessionSerializer(qs, many=True, context={"current_session_id": current_id}).data
        return Response({"data": data})


class SessionRevokeView(APIView):
    permission_classes = [ActionPermission]
    required_action = "auth.session.revoke"

    def get_authz_resource(self) -> Any:
        return getattr(self, "_session_obj", None)

    @extend_schema(responses={204: OpenApiResponse(description="Session revoked")})
    def delete(self, request: Request, session_id: str) -> Response:
        # Query is scoped to the requesting user -> a non-owned id is a 404
        # (do not reveal that another user's session exists). The engine also
        # re-checks ownership as defence-in-depth.
        self._session_obj = get_object_or_404(AuthSession, pk=session_id, user=_user(request))
        self.check_object_permissions(request, self._session_obj)
        ok = auth_service.revoke_session(
            session_id=str(session_id), requesting_user=_user(request), ip=_client_ip(request)
        )
        if not ok:  # pragma: no cover - get_object_or_404 already guards this
            raise AuthorizationError("Not your session.", code="authz.forbidden")
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPingView(APIView):
    """Vertical-privilege-escalation test target: requires an admin permission."""

    permission_classes = [ActionPermission]
    required_action = "admin.ping"

    @extend_schema(responses={200: OpenApiResponse(description="pong")})
    def get(self, request: Request) -> Response:
        from fikisha.identity.authz.actors import actor_from_request

        actor = actor_from_request(request)
        return Response({"pong": True, "roles": sorted(actor.roles)})


class ConfigPublicView(APIView):
    permission_classes = [ActionPermission]
    required_action = "config.read.public"

    @extend_schema(responses={200: OpenApiResponse(description="Public config subset")})
    def get(self, request: Request) -> Response:
        data = config.current()
        return Response(
            {
                "brand": data.get("brand"),
                "locales": data.get("locales"),
                "pilot": data.get("pilot"),
                "vehicle_types": data.get("vehicle_types"),
                "cargo_categories": data.get("cargo_categories"),
                "value_bands": data.get("value_bands"),
                "feature_flags": data.get("feature_flags"),
                "config_version": config.current_version(),
            }
        )


class DemoAtomicOutboxView(APIView):
    """Proves: one DB transaction writes an audit row AND an outbox row atomically.

    ``POST ?fail=1`` raises after both writes -> a test asserts neither row
    survives. DEBUG + ``feature_flags.demo_endpoints`` only.
    """

    permission_classes = [ActionPermission]
    required_action = "demo.atomic.invoke"

    @extend_schema(responses={201: OpenApiResponse(description="Atomic demo executed")})
    def post(self, request: Request) -> Response:
        note = str(request.data.get("note", "phase-2a atomic demo"))[:200]
        fail = request.query_params.get("fail") in {"1", "true", "yes"}

        with transaction.atomic():
            entry = audit.record(
                actor=request.user,
                action="demo.atomic",
                entity_type="demo",
                entity_id=None,
                after={"note": note},
            )
            event = emit(
                event_type="demo.atomic_demo",
                aggregate_type="demo",
                aggregate_id=None,
                payload={"note": note, "audit_seq": entry.seq},
            )
            if fail:
                raise RuntimeError("intentional failure to demonstrate rollback")

        return Response(
            {"audit_seq": entry.seq, "outbox_event_id": event.id, "note": note},
            status=status.HTTP_201_CREATED,
        )
