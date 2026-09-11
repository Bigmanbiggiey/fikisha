"""Database-level append-only enforcement for the incidents/disputes history
tables (dispute-and-liability.md §3 — Evidence/Statement/Resolution/Escalation
are all append-only + audit-logged). Reuses ``fikisha_forbid_mutation()`` from
audit.0003, exactly like negotiation.0002 and jobs.0005.

``Incident`` and ``Dispute`` themselves are NOT append-only here — they carry a
small explicit status workflow (plan §19 Step 8) and are mutated in place by
:mod:`fikisha.incidents.services` under row locks, the same way ``Job`` is
mutated by ``JobLifecycleService``. Only their genuinely historical children
(evidence attachments, statements, resolutions, escalations) are append-only.
"""

from __future__ import annotations

from django.db import migrations

_TABLES = ["incident_evidence", "incident_statement", "resolution", "escalation"]

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
        EXECUTE 'REVOKE UPDATE, DELETE ON incident_evidence FROM app_rw';
        EXECUTE 'REVOKE UPDATE, DELETE ON incident_statement FROM app_rw';
        EXECUTE 'REVOKE UPDATE, DELETE ON resolution FROM app_rw';
        EXECUTE 'REVOKE UPDATE, DELETE ON escalation FROM app_rw';
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0001_initial"),
        ("audit", "0003_append_only_db_guard"),
    ]

    operations = [
        migrations.RunSQL(_TRIGGERS, reverse_sql=_DROP),
        migrations.RunSQL(_GRANTS, reverse_sql=migrations.RunSQL.noop),
    ]
