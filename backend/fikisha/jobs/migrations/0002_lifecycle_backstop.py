"""Database-level lifecycle backstop + append-only guards + custody views.

job-state-machine.md §7 / §4.7, plan §19 Step 3 & ADR-2D-03 / Q-7:

1. **``allowed_job_transition``** seeded from ``jobs.transitions.ALLOWED_PAIRS``
   (the same single source the service uses).
2. **``BEFORE UPDATE OF status ON job``** trigger — rejects any ``status`` change
   not in that table unless ``app.lifecycle_service = 'on'`` (the GUC
   :func:`fikisha.jobs.service.transition` sets after its guards pass). Defence
   in depth: a stray raw ``UPDATE`` cannot corrupt a job's state.
3. **Append-only triggers** on the job-domain immutable tables, reusing
   ``fikisha_forbid_mutation()`` from ``audit.0003``.
4. **Custody / timeline views** — ``job_status_event``, ``chain_of_custody``,
   ``job_timeline`` (no data duplication; ADR-009).
5. **``app.actor_id`` seam** — the service also sets this GUC per transaction so
   a future Row-Level-Security policy (Q-7, deferred to hardening) can read the
   acting principal without a schema change. Nothing reads it yet.
6. **``app_rw`` grants** — applied only if that role exists (prod hardening;
   the role name is environment-specific — see docs/phase-2/security-baseline.md).
"""

from __future__ import annotations

from django.db import migrations

from fikisha.jobs.transitions import ALLOWED_PAIRS

_APPEND_ONLY_TABLES = (
    "job_event",
    "agreement",
    "cancellation_record",
    "failure_record",
    "proof_of_pickup",
    "proof_of_delivery",
    "high_value_approval",
)


def _seed_transitions(apps, schema_editor):
    model = apps.get_model("jobs", "AllowedJobTransition")
    model.objects.all().delete()
    model.objects.bulk_create(
        [model(from_status=frm, to_status=to) for (frm, to) in ALLOWED_PAIRS],
        ignore_conflicts=True,
    )


def _unseed_transitions(apps, schema_editor):
    apps.get_model("jobs", "AllowedJobTransition").objects.all().delete()


_TRIGGER_FN = r"""
CREATE OR REPLACE FUNCTION fikisha_check_job_transition() RETURNS trigger AS $$
BEGIN
    IF NEW.status = OLD.status THEN
        RETURN NEW;
    END IF;
    IF current_setting('app.lifecycle_service', true) = 'on' THEN
        RETURN NEW;
    END IF;
    IF EXISTS (
        SELECT 1 FROM allowed_job_transition
        WHERE from_status = OLD.status AND to_status = NEW.status
    ) THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'illegal job status transition % -> % (not via JobLifecycleService)',
        OLD.status, NEW.status
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS job_status_transition_guard ON job;
CREATE TRIGGER job_status_transition_guard
    BEFORE UPDATE OF status ON job
    FOR EACH ROW EXECUTE FUNCTION fikisha_check_job_transition();
"""

_TRIGGER_FN_REVERSE = """
DROP TRIGGER IF EXISTS job_status_transition_guard ON job;
DROP FUNCTION IF EXISTS fikisha_check_job_transition() CASCADE;
"""


def _append_only(table: str) -> str:
    return f"""
    DROP TRIGGER IF EXISTS {table}_no_update ON {table};
    DROP TRIGGER IF EXISTS {table}_no_delete ON {table};
    CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION fikisha_forbid_mutation();
    CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION fikisha_forbid_mutation();
    """


def _drop_append_only(table: str) -> str:
    return f"""
    DROP TRIGGER IF EXISTS {table}_no_update ON {table};
    DROP TRIGGER IF EXISTS {table}_no_delete ON {table};
    """


_VIEWS = """
CREATE OR REPLACE VIEW job_status_event AS
    SELECT * FROM job_event WHERE category = 'STATUS_TRANSITION';

CREATE OR REPLACE VIEW chain_of_custody AS
    SELECT * FROM job_event WHERE is_custody = true;

CREATE OR REPLACE VIEW job_timeline AS
    SELECT * FROM job_event;
"""

_VIEWS_REVERSE = """
DROP VIEW IF EXISTS job_status_event;
DROP VIEW IF EXISTS chain_of_custody;
DROP VIEW IF EXISTS job_timeline;
"""

_GRANTS = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
        EXECUTE 'REVOKE UPDATE, DELETE ON job_event, agreement, cancellation_record,
                 failure_record, proof_of_pickup, proof_of_delivery, high_value_approval
                 FROM app_rw';
        EXECUTE 'GRANT SELECT ON job_status_event, chain_of_custody, job_timeline TO app_rw';
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0001_initial"),
        ("audit", "0003_append_only_db_guard"),
    ]

    operations = [
        migrations.RunPython(_seed_transitions, _unseed_transitions),
        migrations.RunSQL(_TRIGGER_FN, reverse_sql=_TRIGGER_FN_REVERSE),
        *[
            migrations.RunSQL(_append_only(t), reverse_sql=_drop_append_only(t))
            for t in _APPEND_ONLY_TABLES
        ],
        migrations.RunSQL(_VIEWS, reverse_sql=_VIEWS_REVERSE),
        migrations.RunSQL(_GRANTS, reverse_sql=migrations.RunSQL.noop),
    ]
