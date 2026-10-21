"""geography coordinates, timestamptz, unique users, carrier fk

Revision ID: efd56aed3542
Revises: a783dd2776aa
Create Date: 2026-10-21 13:24:46.326752

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography, Geometry

# revision identifiers, used by Alembic.
revision: str = 'efd56aed3542'
down_revision: Union[str, Sequence[str], None] = 'a783dd2776aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POINT_TABLES = ("stops", "addresses")

NAIVE_TIMESTAMPS = (
    ("stops_metrics", "click_time"),
    ("addresses_metrics", "click_time"),
    ("web_users", "last_logged_in"),
    ("web_users", "premium_expires"),
)

UNIQUE_CONSTRAINTS = (
    ("scr_api_users_email_key", "scr_api_users", "email"),
    ("scr_api_users_username_key", "scr_api_users", "username"),
    ("web_users_email_unique", "web_users", "email"),
    ("web_users_username_unique", "web_users", "username"),
)


def upgrade() -> None:
    """Upgrade schema."""
    for table in POINT_TABLES:
        op.alter_column(
            table,
            "coordinates",
            type_=Geography("POINT", srid=4326, spatial_index=False),
            postgresql_using="ST_SetSRID(coordinates, 4326)::geography",
        )

    for table, column in NAIVE_TIMESTAMPS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )

    for name, table, column in UNIQUE_CONSTRAINTS:
        op.create_unique_constraint(name, table, [column])

    op.create_foreign_key(
        "scr_targets_carrier_id_fkey", "scr_targets", "carriers",
        ["carrier_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("scr_targets_carrier_id_fkey", "scr_targets",
                       type_="foreignkey")

    for name, table, _ in UNIQUE_CONSTRAINTS:
        op.drop_constraint(name, table, type_="unique")

    for table, column in NAIVE_TIMESTAMPS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )

    for table in POINT_TABLES:
        op.alter_column(
            table,
            "coordinates",
            type_=Geometry("POINT", spatial_index=False),
            postgresql_using="ST_SetSRID(coordinates::geometry, 0)",
        )
