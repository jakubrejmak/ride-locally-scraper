"""priority, claim, and NOTIFY triggers

Revision ID: 7b3c2f8a1d94
Revises: 4ab5a25ccf6f
Create Date: 2026-07-07 09:00:00.000000

Adds worker-side scheduling primitives:
  - priority + next_due_at + claim fields on scr_targets
  - priority + should_process + claim fields on scr_runs
  - covering indexes for the claim query
  - LISTEN/NOTIFY triggers so idle workers wake immediately on new work

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b3c2f8a1d94"
down_revision: Union[str, Sequence[str], None] = "4ab5a25ccf6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- scr_targets columns ------------------------------------------------
    # server_default on priority so existing rows backfill to 0 without a
    # separate UPDATE. we drop the server_default at the end so future INSERTs
    # go through the ORM's Python default and the schema stays declarative.
    op.add_column(
        "scr_targets",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "scr_targets",
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "scr_targets",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "scr_targets",
        sa.Column("claimed_by", sa.String(length=255), nullable=True),
    )

    # existing targets become immediately due; matches the "first poll picks
    # up everything active" behavior of the old producer loop.
    op.execute("UPDATE scr_targets SET next_due_at = now() WHERE is_active")

    op.alter_column("scr_targets", "priority", server_default=None)

    # --- scr_runs columns ---------------------------------------------------
    op.add_column(
        "scr_runs",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "scr_runs",
        sa.Column(
            "should_process", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "scr_runs",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "scr_runs",
        sa.Column("claimed_by", sa.String(length=255), nullable=True),
    )

    op.alter_column("scr_runs", "priority", server_default=None)
    op.alter_column("scr_runs", "should_process", server_default=None)

    # --- indexes for the claim queries -------------------------------------
    # scr_targets claim: WHERE is_active AND claimed_at IS NULL
    #                    AND (next_due_at IS NULL OR next_due_at <= now())
    #                    ORDER BY priority DESC, next_due_at ASC NULLS FIRST
    op.execute(
        "CREATE INDEX ix_scr_targets_claim "
        "ON scr_targets (is_active, claimed_at, priority DESC, next_due_at) "
        "WHERE is_active AND claimed_at IS NULL"
    )
    # scr_runs claim: WHERE status = 'pending' AND should_process AND claimed_at IS NULL
    #                 ORDER BY priority DESC, created_at ASC
    op.execute(
        "CREATE INDEX ix_scr_runs_claim "
        "ON scr_runs (status, claimed_at, priority DESC, created_at) "
        "WHERE status = 'pending' AND should_process AND claimed_at IS NULL"
    )

    # --- NOTIFY triggers ----------------------------------------------------
    # target_ready fires when new work becomes visible to the claim query:
    #   - fresh INSERT
    #   - next_due_at moved earlier (includes NULL -> value, so run-now works)
    #   - priority raised
    #   - claim released (reaper or normal completion path)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION scr_notify_target_ready() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                PERFORM pg_notify('scr_target_ready', NEW.id::text);
                RETURN NEW;
            END IF;

            IF (NEW.next_due_at IS DISTINCT FROM OLD.next_due_at
                AND (OLD.next_due_at IS NULL OR NEW.next_due_at < OLD.next_due_at))
               OR NEW.priority > OLD.priority
               OR (OLD.claimed_at IS NOT NULL AND NEW.claimed_at IS NULL) THEN
                PERFORM pg_notify('scr_target_ready', NEW.id::text);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER scr_targets_notify "
        "AFTER INSERT OR UPDATE ON scr_targets "
        "FOR EACH ROW EXECUTE FUNCTION scr_notify_target_ready();"
    )

    # run_ready fires on INSERT of a runnable pending row. status flips happen
    # via the worker's own claim path, so they don't need to notify.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION scr_notify_run_ready() RETURNS trigger AS $$
        BEGIN
            IF NEW.status = 'pending' AND NEW.should_process THEN
                PERFORM pg_notify('scr_run_ready', NEW.id::text);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER scr_runs_notify "
        "AFTER INSERT ON scr_runs "
        "FOR EACH ROW EXECUTE FUNCTION scr_notify_run_ready();"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS scr_runs_notify ON scr_runs")
    op.execute("DROP FUNCTION IF EXISTS scr_notify_run_ready()")
    op.execute("DROP TRIGGER IF EXISTS scr_targets_notify ON scr_targets")
    op.execute("DROP FUNCTION IF EXISTS scr_notify_target_ready()")

    op.execute("DROP INDEX IF EXISTS ix_scr_runs_claim")
    op.execute("DROP INDEX IF EXISTS ix_scr_targets_claim")

    op.drop_column("scr_runs", "claimed_by")
    op.drop_column("scr_runs", "claimed_at")
    op.drop_column("scr_runs", "should_process")
    op.drop_column("scr_runs", "priority")

    op.drop_column("scr_targets", "claimed_by")
    op.drop_column("scr_targets", "claimed_at")
    op.drop_column("scr_targets", "next_due_at")
    op.drop_column("scr_targets", "priority")
