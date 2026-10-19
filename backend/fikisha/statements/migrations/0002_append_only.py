"""Database-level append-only enforcement for the statement tables
(Commission & Statements S-1, ADR-2D-42). Reuses
``fikisha_forbid_mutation()`` from audit.0003, exactly like
jobs.0007_commission_append_only.
"""

from __future__ import annotations

from django.db import migrations

_TABLES = ("commission_statement", "statement_line", "statement_settlement")


def _triggers(table: str) -> str:
    return f"""
DROP TRIGGER IF EXISTS {table}_no_update ON {table};
DROP TRIGGER IF EXISTS {table}_no_delete ON {table};
CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table}
    FOR EACH ROW EXECUTE FUNCTION fikisha_forbid_mutation();
CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table}
    FOR EACH ROW EXECUTE FUNCTION fikisha_forbid_mutation();
"""


def _drop(table: str) -> str:
    return f"""
DROP TRIGGER IF EXISTS {table}_no_update ON {table};
DROP TRIGGER IF EXISTS {table}_no_delete ON {table};
"""


def _grants(table: str) -> str:
    return f"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
        EXECUTE 'REVOKE UPDATE, DELETE ON {table} FROM app_rw';
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("statements", "0001_initial"),
        ("audit", "0003_append_only_db_guard"),
    ]

    operations = [
        op
        for table in _TABLES
        for op in (
            migrations.RunSQL(_triggers(table), reverse_sql=_drop(table)),
            migrations.RunSQL(_grants(table), reverse_sql=migrations.RunSQL.noop),
        )
    ]
