"""Fikisha application package.

A modular monolith: each subpackage is a bounded module (a Django app). Modules
interact only through a module's public ``services``/``authz`` surface or via
domain events on the transactional outbox — never by importing another module's
models directly. See ``docs/phase-1/domain-architecture.md``.

Phase 2A foundation modules: common, audit, outbox, platform_config, identity,
storage, observability. Business-domain modules (jobs, negotiation, operators,
...) are introduced in later phases.
"""
