"""Typed negotiation errors (RFC-9457 via the common handler)."""

from __future__ import annotations

from rest_framework import status

from fikisha.common.exceptions import ConflictError, DomainError


class JobNotOpenForNegotiation(ConflictError):
    default_code = "job_not_open_for_negotiation"
    default_detail = "This job is no longer open for negotiation."


class ThreadNotActive(ConflictError):
    default_code = "thread_not_active"
    default_detail = "This negotiation thread is closed."


class NoThreadYet(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "no_negotiation_thread"
    default_detail = "There is no negotiation thread yet; the operator must make the first offer."


class InvalidOffer(DomainError):
    default_code = "invalid_offer"
    default_detail = "The offer amount is invalid."


class NothingToAccept(DomainError):
    default_code = "nothing_to_accept"
    default_detail = "There is no active standing offer from the other party to accept."


class NotANegotiationParty(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "not_a_negotiation_party"
    default_detail = "You are not a party to this negotiation."
