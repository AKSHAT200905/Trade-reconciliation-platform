from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recon_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("internal_count", sa.Integer(), nullable=False),
        sa.Column("custodian_count", sa.Integer(), nullable=False),
        sa.Column("matched_count", sa.Integer(), nullable=False),
        sa.Column("break_count", sa.Integer(), nullable=False),
        sa.Column("match_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("total_exposure", sa.Numeric(20, 2), nullable=False),
        sa.Column("price_tolerance_bps", sa.Numeric(8, 4), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recon_runs_trade_date", "recon_runs", ["trade_date"])

    op.create_table(
        "breaks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("recon_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trade_ref", sa.String(64), nullable=False),
        sa.Column("break_type", sa.String(32), nullable=False),
        sa.Column("field", sa.String(32), nullable=True),
        sa.Column("internal_value", sa.String(255), nullable=True),
        sa.Column("custodian_value", sa.String(255), nullable=True),
        sa.Column("exposure", sa.Numeric(20, 2), nullable=False),
        sa.Column("instrument", sa.String(32), nullable=False),
        sa.Column("counterparty", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("resolution_comment", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(64), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="ck_breaks_status"),
        sa.CheckConstraint("exposure >= 0", name="ck_breaks_exposure_non_negative"),
    )
    op.create_index("ix_breaks_run_status", "breaks", ["run_id", "status"])
    op.create_index("ix_breaks_trade_ref", "breaks", ["trade_ref"])


def downgrade() -> None:
    op.drop_index("ix_breaks_trade_ref", table_name="breaks")
    op.drop_index("ix_breaks_run_status", table_name="breaks")
    op.drop_table("breaks")
    op.drop_index("ix_recon_runs_trade_date", table_name="recon_runs")
    op.drop_table("recon_runs")
