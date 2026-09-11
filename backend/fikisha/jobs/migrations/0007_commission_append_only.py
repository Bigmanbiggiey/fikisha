"""Database-level append-only enforcement for the commission history tables
(Step 9, plan §19, brief §20 — "Historical commission records must be
append-only... use the existing DB-trigger pattern"). Reuses
``fikisha_forbid_mutation()`` from audit.0003, exactly like negotiation.0002,
jobs.0005, and incidents.0002.
"""

from __future__ import annotations

from django.db import migrations

_TABLES = ["commission_record", "commission_adjustment"]

_TRIGGERS = "\n".join(
    f"""
DROP TRIGGER IF EXISTS {table}_no_update ON {table};
DROP TRIGGER IF EXISTS {table}_no_delete ON {table};
CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table}
    FOR EACH ROW EXECUTE FUNCTION fikisha_forbid_mutation();
CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table}
    FOR EACH ROW EXECUTE FUNCTION fikisha_forbid_mutation();
"""
    for table in _TABLES
)

_DROP = "\n".join(
    f"""
DROP TRIGGER IF EXISTS {table}_no_update ON {table};
DROP TRIGGER IF EXISTS {table}_no_delete ON {table};
"""
    for table in _TABLES
)

_GRANTS = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
        EXECUTE 'REVOKE UPDATE, DELETE ON commission_record FROM app_rw';
        EXECUTE 'REVOKE UPDATE, DELETE ON commission_adjustment FROM app_rw';
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0006_commissionrecord_commissionadjustment_and_more"),
        ("audit", "0003_append_only_db_guard"),
    ]

    operations = [
        migrations.RunSQL(_TRIGGERS, reverse_sql=_DROP),
        migrations.RunSQL(_GRANTS, reverse_sql=migrations.RunSQL.noop),
    ]
