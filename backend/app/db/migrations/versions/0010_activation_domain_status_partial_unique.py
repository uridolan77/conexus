"""Partial unique indexes: one Active and one Canary activation per domain_key.

Revision ID: 0010_activation_domain_status_partial_unique
Revises: 0009_m5_usage_events_and_model_aliases
Create Date: 2026-05-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0010_activation_domain_status_partial_unique"
down_revision = "0009_m5_usage_events_and_model_aliases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_gw_profile_activation_domain_active",
        "gateway_adapter_profile_activations",
        ["domain_key"],
        unique=True,
        postgresql_where=sa.text("status = 'Active'"),
        sqlite_where=sa.text("status = 'Active'"),
    )
    op.create_index(
        "uq_gw_profile_activation_domain_canary",
        "gateway_adapter_profile_activations",
        ["domain_key"],
        unique=True,
        postgresql_where=sa.text("status = 'Canary'"),
        sqlite_where=sa.text("status = 'Canary'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_gw_profile_activation_domain_canary",
        table_name="gateway_adapter_profile_activations",
    )
    op.drop_index(
        "uq_gw_profile_activation_domain_active",
        table_name="gateway_adapter_profile_activations",
    )
