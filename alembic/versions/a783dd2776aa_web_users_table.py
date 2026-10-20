"""web_users table

Revision ID: a783dd2776aa
Revises: dd9ba6407559
Create Date: 2026-10-20 18:20:07.147893

web/app/db/schema.ts defined web_users but drizzle's 0000 migration never
created it. If a database already has it (e.g. from `drizzle-kit push`),
stamp this revision instead of applying it:
    alembic stamp a783dd2776aa
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a783dd2776aa'
down_revision: Union[str, Sequence[str], None] = 'dd9ba6407559'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USER_ROLES = ("sys_superuser", "sys_admin", "sys_moderator", "sub_default", "sub_premium")


def upgrade() -> None:
    """Upgrade schema."""
    postgresql.ENUM(*USER_ROLES, name="user_role").create(op.get_bind())

    op.create_table(
        "web_users",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", postgresql.ENUM(*USER_ROLES, name="user_role", create_type=False), nullable=True),
        sa.Column("last_logged_in", sa.DateTime(), nullable=True),
        sa.Column("premium_expires", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("web_users")
    postgresql.ENUM(name="user_role").drop(op.get_bind())
