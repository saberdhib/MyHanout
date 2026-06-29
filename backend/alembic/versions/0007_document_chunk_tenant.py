"""organization_id sur document_chunk (RAG tenant-scopé) — gaps techniques.

Revision ID: 0007_doc_chunk_tenant
Revises: 0006_agent_memory
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_doc_chunk_tenant"
down_revision: str | None = "0006_agent_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("document_chunk", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE document_chunk SET organization_id = "
        "(SELECT id FROM organization WHERE slug='default')"
    )
    op.alter_column("document_chunk", "organization_id", nullable=False)
    op.create_foreign_key(
        "fk_document_chunk_organization", "document_chunk", "organization", ["organization_id"], ["id"]
    )
    op.create_index("ix_document_chunk_organization_id", "document_chunk", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_document_chunk_organization_id", "document_chunk")
    op.drop_constraint("fk_document_chunk_organization", "document_chunk", type_="foreignkey")
    op.drop_column("document_chunk", "organization_id")
