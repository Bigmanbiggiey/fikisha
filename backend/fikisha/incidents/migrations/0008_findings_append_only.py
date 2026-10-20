"""Database-level append-only enforcement for findings and unfounded-report
records (trust-and-disputes plan A2, A3). Reuses ``fikisha_forbid_mutation()``
from audit.0003, like incidents.0002.
"""

from __future__ import annotations

from django.db import migrations

_TABLES = ["incident_finding", "incident_finding_party", "unfounded_report"]

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

_GRANTS = (
    """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
"""
    + "".join(f"        EXECUTE 'REVOKE UPDATE, DELETE ON {t} FROM app_rw';\n" for t in _TABLES)
    + """    END IF;
END
$$;
"""
)


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0007_findings"),
        ("audit", "0003_append_only_db_guard"),
    ]

    operations = [
        migrations.RunSQL(_TRIGGERS, reverse_sql=_DROP),
        migrations.RunSQL(_GRANTS, reverse_sql=migrations.RunSQL.noop),
    ]
