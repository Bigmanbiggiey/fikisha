"""Typed Incidents/Disputes-domain errors (mapped to RFC-9457 problem+json)."""

from __future__ import annotations

from rest_framework import status

from fikisha.common.exceptions import AuthorizationError, ConflictError, DomainError


class NotIncidentParty(AuthorizationError):
    default_code = "not_incident_party"
    default_detail = "You are not a party to this job and may not act on this incident."


class IncidentNotFound(DomainError):
    default_code = "incident_not_found"
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "No such incident."


class DisputeNotFound(DomainError):
    default_code = "dispute_not_found"
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "No such dispute."


class IncidentAlreadyResolved(ConflictError):
    default_code = "incident_already_resolved"
    default_detail = "This incident is already resolved."


class DisputeAlreadyOpen(ConflictError):
    default_code = "dispute_already_open"
    default_detail = "This job already has an open dispute."


class DisputeAlreadyResolved(ConflictError):
    default_code = "dispute_already_resolved"
    default_detail = "This dispute has already been resolved and cannot be reopened."


class NotAuthorisedForIncidentReview(AuthorizationError):
    default_code = "not_authorised_for_incident_review"
    default_detail = "Incident review requires an administrative role."


class NotAuthorisedForBindingResolution(AuthorizationError):
    default_code = "not_authorised_for_binding_resolution"
    default_detail = "Binding resolution above the Standard band requires a Platform Administrator."


class InvalidResolutionRouting(DomainError):
    default_code = "invalid_resolution_routing"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "A dispute may only be routed to COMPLETED, FAILED or CANCELLED."


class RationaleRequired(DomainError):
    default_code = "rationale_required"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "A resolution rationale is required."


class InvalidIncidentType(DomainError):
    default_code = "invalid_incident_type"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "That is not a recognised incident type."


class InvalidIncidentSeverity(DomainError):
    default_code = "invalid_incident_severity"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "That is not a recognised incident severity."


class InvalidResolutionOutcome(DomainError):
    default_code = "invalid_resolution_outcome"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "That is not a recognised resolution outcome code."


class StatementTextRequired(DomainError):
    default_code = "statement_text_required"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Statement text is required."
