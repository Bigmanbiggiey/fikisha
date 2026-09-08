"""Database-level append-only enforcement.

Phase 1 NFR-AUD-3 / database-design.md §1: audit + config-version rows must be
protected from ``UPDATE`` / ``DELETE`` at the storage layer, not only in
application code. Two mechanisms, both applied here:

1. **Triggers** (portable, works in dev + prod): a ``BEFORE UPDATE/DELETE``
   trigger on ``audit_log_entry`` and ``platform_config_version`` raises.
2. **Role privileges** (prod hardening, documented, not run here because the
   runtime DB role name is environment-specific — see
   docs/phase-2/security-baseline.md):

       REVOKE UPDATE, DELETE ON audit_log_entry          FROM <app_rw_role>;
       REVOKE UPDATE, DELETE ON platform_config_version  FROM <app_rw_role>;

The application-layer guard (``AppendOnlyModel`` / ``AppendOnlyQuerySet``) sits
on top of both and gives a friendly error before the DB is touched.
"""

from __future__ import annotations

from django.db import migrations

_CREATE_FN = """
CREATE OR REPLACE FUNCTION fikisha_forbid_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'relation % is append-only; % is not permitted',
        TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;
"""

_DROP_FN = "DROP FUNCTION IF EXISTS fikisha_forbid_mutation() CASCADE;"


def _triggers(table: str) -> str:
    return f"""
    DROP TRIGGER IF EXISTS {table}_no_update ON {table};
    DROP TRIGGER IF EXISTS {table}_no_delete ON {table};
    CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION fikisha_forbid_mutation();
    CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION fikisha_forbid_mutation();
    """


def _drop_triggers(table: str) -> str:
    return f"""
    DROP TRIGGER IF EXISTS {table}_no_update ON {table};
    DROP TRIGGER IF EXISTS {table}_no_delete ON {table};
    """


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_initial"),
        ("platform_config", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(_CREATE_FN, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(
            _triggers("audit_log_entry"), reverse_sql=_drop_triggers("audit_log_entry")
        ),
        migrations.RunSQL(
            _triggers("platform_config_version"),
            reverse_sql=_drop_triggers("platform_config_version"),
        ),
        migrations.RunSQL(migrations.RunSQL.noop, reverse_sql=_DROP_FN),
    ]
