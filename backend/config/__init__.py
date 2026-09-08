"""Fikisha Django project package (settings, URLs, Celery wiring)."""

from config.celery import app as celery_app

__all__ = ("celery_app",)
