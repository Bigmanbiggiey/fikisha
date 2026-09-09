"""Business — business accounts, their members, and their locations.

Phase 1 domain-architecture §3.2. A bounded module: it exposes its behaviour
through ``fikisha.business.services`` and its authorization through
``fikisha.business.authz`` / policies. No other module imports its models
directly (cross-module references use string FKs).
"""
