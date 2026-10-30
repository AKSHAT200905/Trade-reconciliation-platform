from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trade_ref", sa.String(64), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("instrument", sa.String(32), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("counterparty", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "trade_ref", name="uq_trades_source_ref"),
        sa.CheckConstraint("source IN ('INTERNAL', 'CUSTODIAN')", name="ck_trades_source"),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_trades_side"),
        sa.CheckConstraint("quantity > 0", name="ck_trades_quantity_positive"),
        sa.CheckConstraint("price > 0", name="ck_trades_price_positive"),
    )
    op.create_index("ix_trades_trade_date_source", "trades", ["trade_date", "source"])


def downgrade() -> None:
    op.drop_index("ix_trades_trade_date_source", table_name="trades")
    op.drop_table("trades")
