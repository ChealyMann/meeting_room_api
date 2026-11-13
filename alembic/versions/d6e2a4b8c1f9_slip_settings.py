"""the request slip's settings: Director of Cabinet and the address line (one row)

Revision ID: d6e2a4b8c1f9
Revises: c3d8e1f5a7b2
Create Date: 2026-11-13 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "d6e2a4b8c1f9"
down_revision: str | Sequence[str] | None = "c3d8e1f5a7b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_ADDRESS_KH = (
    "ប្រអប់សំបុត្រលេខ ២៥, ផ្ទះលេខ ៨៨ ផ្លូវលេខ ១០២ កែងផ្លូវលេខ ១៩ សង្កាត់វត្តភ្នំ ខណ្ឌដូនពេញ "
    "រាជធានីភ្នំពេញ, ទូរស័ព្ទ ៖ (៨៥៥-២៣) ៧២២ ៥៦៣, ទូរស័ព្ទ / ទូរសារ ៖ (៨៥៥-២៣) ៩២៦ ១១៧"
)


def upgrade() -> None:
    table = op.create_table(
        "slip_settings",
        sa.Column("id", mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("director_user_id", mysql.INTEGER(unsigned=True), nullable=True),
        sa.Column("address_kh", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["director_user_id"],
            ["users.id"],
            name=op.f("fk_slip_settings_director_user_id_users"),
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_slip_settings")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        op.f("ix_slip_settings_director_user_id"), "slip_settings", ["director_user_id"]
    )
    now = sa.func.utc_timestamp()
    op.execute(
        table.insert().values(id=1, address_kh=DEFAULT_ADDRESS_KH, created_at=now, updated_at=now)
    )


def downgrade() -> None:
    op.drop_table("slip_settings")
