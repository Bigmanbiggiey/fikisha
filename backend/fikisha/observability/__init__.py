"""Observability foundation — health probes and metric hooks.

Full pipeline (analytics_event -> metric_daily -> dashboard/export) is a later
phase. Phase 2A provides: structured logging (fikisha.common.logging_setup),
request ids (fikisha.common.request_id), health/readiness probes, and a small
metrics-hook seam.
"""
