from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReconRun(Base):
    __tablename__ = "recon_runs"
    __table_args__ = (Index("ix_recon_runs_trade_date", "trade_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="COMPLETED")
    internal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    custodian_count: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False)
    break_count: Mapped[int] = mapped_column(Integer, nullable=False)
    match_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    total_exposure: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    price_tolerance_bps: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    breaks: Mapped[list["Break"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Break(Base):
    __tablename__ = "breaks"
    __table_args__ = (
        Index("ix_breaks_run_status", "run_id", "status"),
        Index("ix_breaks_trade_ref", "trade_ref"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("recon_runs.id", ondelete="CASCADE"), nullable=False)
    trade_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    break_type: Mapped[str] = mapped_column(String(32), nullable=False)
    field: Mapped[str | None] = mapped_column(String(32), nullable=True)
    internal_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custodian_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exposure: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    instrument: Mapped[str] = mapped_column(String(32), nullable=False)
    counterparty: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    resolution_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    run: Mapped[ReconRun] = relationship(back_populates="breaks")
