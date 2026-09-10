"""Database-level append-only enforcement for ``negotiation_entry``.

negotiation-architecture.md §7 / plan §5: the negotiation history is immutable —
``INSERT, SELECT`` only, an attempted ``UPDATE`` / ``DELETE`` raises. Reuses the
shared ``fikisha_forbid_mutation()`` trigger function from ``audit.0003``.

``negotiation_thread`` is intentionally **not** guarded — its ``status``
(ACTIVE → SUPERSEDED / CLOSED) and ``closed_at`` are mutable bookkeeping.
An entry's ACTIVE/SUPERSEDED/EXPIRED status is derived at read time (ADR-2D-11),
so no entry row is ever updated.
"""

from __future__ import annotations

from django.db import migrations

_TABLE = "negotiation_entry"

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

_GRANTS = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
        EXECUTE 'REVOKE UPDATE, DELETE ON negotiation_entry FROM app_rw';
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("negotiation", "0001_initial"),
        ("audit", "0003_append_only_db_guard"),
    ]

    operations = [
        migrations.RunSQL(_TRIGGERS, reverse_sql=_DROP),
        migrations.RunSQL(_GRANTS, reverse_sql=migrations.RunSQL.noop),
    ]
