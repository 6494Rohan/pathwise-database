"""enable postgis pgvector pg_trgm

Revision ID: 62fc8c13dcec
Revises: 
Create Date: 2026-10-27 21:49:30.035416

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '62fc8c13dcec'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EXTENSIONS = ("postgis", "vector", "pg_trgm")


def upgrade() -> None:
    for extension in EXTENSIONS:
        op.execute(f"CREATE EXTENSION IF NOT EXISTS {extension}")


def downgrade() -> None:
    for extension in reversed(EXTENSIONS):
        op.execute(f"DROP EXTENSION IF EXISTS {extension}")
