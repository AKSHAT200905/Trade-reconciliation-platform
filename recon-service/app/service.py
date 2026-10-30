from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine import ReconResult
from app.models import Break, ReconRun
from app.schemas import BreakStatus, BreakUpdate


def save_run(db: Session, trade_date: date, result: ReconResult, tolerance_bps: Decimal, started_at: datetime) -> ReconRun:
    run = ReconRun(
        trade_date=trade_date,
        status="COMPLETED",
        internal_count=result.internal_count,
        custodian_count=result.custodian_count,
        matched_count=len(result.matched_refs),
        break_count=len(result.breaks),
        match_rate=result.match_rate,
        total_exposure=result.total_exposure,
        price_tolerance_bps=tolerance_bps,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
    )
    run.breaks = [
        Break(
            trade_ref=b.trade_ref,
            break_type=b.break_type.value,
            field=b.field,
            internal_value=b.internal_value,
            custodian_value=b.custodian_value,
            exposure=b.exposure,
            instrument=b.instrument,
            counterparty=b.counterparty,
            status=BreakStatus.OPEN.value,
        )
        for b in result.breaks
    ]
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def list_runs(db: Session, limit: int) -> list[ReconRun]:
    return list(db.scalars(select(ReconRun).order_by(ReconRun.id.desc()).limit(limit)))


def get_run(db: Session, run_id: int) -> ReconRun | None:
    return db.get(ReconRun, run_id)


def list_breaks(db: Session, run_id: int, status: BreakStatus | None, break_type: str | None) -> list[Break]:
    query = select(Break).where(Break.run_id == run_id)
    if status is not None:
        query = query.where(Break.status == status.value)
    if break_type is not None:
        query = query.where(Break.break_type == break_type)
    return list(db.scalars(query.order_by(Break.exposure.desc(), Break.trade_ref, Break.id)))


def update_break(db: Session, break_id: int, update: BreakUpdate) -> Break | None:
    item = db.get(Break, break_id)
    if item is None:
        return None
    if update.status == BreakStatus.RESOLVED:
        item.status = BreakStatus.RESOLVED.value
        item.resolution_comment = update.comment
        item.resolved_by = update.resolved_by or "ops-analyst"
        item.resolved_at = datetime.now(timezone.utc)
    else:
        item.status = BreakStatus.OPEN.value
        item.resolution_comment = None
        item.resolved_by = None
        item.resolved_at = None
    db.commit()
    db.refresh(item)
    return item


def latest_run_ids(db: Session) -> list[int]:
    latest = select(func.max(ReconRun.id)).group_by(ReconRun.trade_date)
    return list(db.scalars(latest))


def summary(db: Session) -> dict:
    run_ids = latest_run_ids(db)
    total_runs = db.scalar(select(func.count(ReconRun.id))) or 0
    latest_run = db.scalar(select(ReconRun).order_by(ReconRun.id.desc()).limit(1))

    counts = {BreakStatus.OPEN.value: 0, BreakStatus.RESOLVED.value: 0}
    open_exposure = Decimal("0.00")
    by_type: list[dict] = []
    if run_ids:
        for status, count in db.execute(
            select(Break.status, func.count(Break.id)).where(Break.run_id.in_(run_ids)).group_by(Break.status)
        ):
            counts[status] = int(count)
        rows = db.execute(
            select(Break.break_type, func.count(Break.id), func.coalesce(func.sum(Break.exposure), 0))
            .where(Break.run_id.in_(run_ids), Break.status == BreakStatus.OPEN.value)
            .group_by(Break.break_type)
            .order_by(func.count(Break.id).desc(), Break.break_type)
        ).all()
        for break_type, count, exposure in rows:
            exposure = Decimal(str(exposure)).quantize(Decimal("0.01"))
            open_exposure += exposure
            by_type.append({"break_type": break_type, "count": int(count), "exposure": exposure})

    return {
        "total_runs": int(total_runs),
        "dates_reconciled": len(run_ids),
        "open_breaks": counts[BreakStatus.OPEN.value],
        "resolved_breaks": counts[BreakStatus.RESOLVED.value],
        "open_exposure": open_exposure.quantize(Decimal("0.01")),
        "latest_run": latest_run,
        "open_breaks_by_type": by_type,
    }
