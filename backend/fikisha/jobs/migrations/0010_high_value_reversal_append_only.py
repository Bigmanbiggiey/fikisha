"""Database-level append-only enforcement for ``high_value_reversal``
(founder decision 2026-10-14). Reuses ``fikisha_forbid_mutation()`` from
audit.0003, like 0007_commission_append_only.
"""

from __future__ import annotations

from django.db import migrations

_TABLE = "high_value_reversal"

_TRIGGERS = f"""
DROP TRIGGER IF EXISTS {_TABLE}_no_update ON {_TABLE};
DROP TRIGGER IF EXISTS {_TABLE}_no_delete ON {_TABLE};
CREATE TRIGGER {_TABLE}_no_update BEFORE UPDATE ON {_TABLE}
    FOR EACH ROW EXECUTE FUNCTION fikisha_forbid_mutation();
CREATE TRIGGER {_TABLE}_no_delete BEFORE DELETE ON {_TABLE}
    FOR EACH ROW EXECUTE FUNCTION fikisha_forbid_mutation();
"""

_DROP = f"""
DROP TRIGGER IF EXISTS {_TABLE}_no_update ON {_TABLE};
DROP TRIGGER IF EXISTS {_TABLE}_no_delete ON {_TABLE};
"""

_GRANTS = f"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
        EXECUTE 'REVOKE UPDATE, DELETE ON {_TABLE} FROM app_rw';
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0009_high_value_reversal"),
        ("audit", "0003_append_only_db_guard"),
    ]

    operations = [
        migrations.RunSQL(_TRIGGERS, reverse_sql=_DROP),
        migrations.RunSQL(_GRANTS, reverse_sql=migrations.RunSQL.noop),
    ]
