from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    bind = op.get_bind()
    return set(sa.inspect(bind).get_table_names())


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    tables = _tables()
    if "secrets" not in tables:
        op.create_table(
            "secrets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("ciphertext", sa.String(), nullable=False),
            sa.Column("nonce", sa.String(), nullable=False),
            sa.Column("crypto_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("name"),
        )
        op.create_index("ix_secrets_name", "secrets", ["name"])
    elif "crypto_version" not in _columns("secrets"):
        op.add_column("secrets", sa.Column("crypto_version", sa.Integer(), nullable=False, server_default="1"))

    tables = _tables()
    if "wrap_tokens" not in tables:
        op.create_table(
            "wrap_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("token_hash", sa.String(), nullable=False),
            sa.Column("secret_name", sa.String(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index("ix_wrap_tokens_token_hash", "wrap_tokens", ["token_hash"])
        op.create_index("ix_wrap_tokens_secret_name", "wrap_tokens", ["secret_name"])

    if "audit_events" not in _tables():
        op.create_table(
            "audit_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_type", sa.String(), nullable=False),
            sa.Column("subject", sa.String(), nullable=True),
            sa.Column("outcome", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("wrap_tokens")
    op.drop_table("secrets")
