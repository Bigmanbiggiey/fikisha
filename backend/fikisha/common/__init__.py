"""Shared, cross-cutting concerns used by every bounded module.

Nothing domain-specific lives here. Contents: UUIDv7 primary keys, base model
mixins (timestamped / append-only), the Money value type, request-id plumbing,
structured-logging config, the problem+json exception handler, cursor
pagination, and a Redis-backed rate limiter.
"""
