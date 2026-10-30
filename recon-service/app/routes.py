import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import PRICE_TOLERANCE_BPS
from app.db import get_db
from app.engine import BreakType, reconcile
from app.schemas import BreakOut, BreakStatus, BreakUpdate, RunOut, RunRequest, Summary
from app.trade_client import TradeServiceClient, TradeServiceError, get_trade_client
from app import service

router = APIRouter(prefix="/api/recon", tags=["reconciliation"])

EXPORT_COLUMNS = [
    "trade_ref",
    "break_type",
    "field",
    "internal_value",
    "custodian_value",
    "exposure",
    "instrument",
    "counterparty",
    "status",
    "resolution_comment",
    "resolved_by",
]


def _require_run(db: Session, run_id: int):
    run = service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


@router.post("/runs", response_model=RunOut, status_code=201)
def run_reconciliation(
    request: RunRequest,
    db: Session = Depends(get_db),
    client: TradeServiceClient = Depends(get_trade_client),
):
    started_at = datetime.now(timezone.utc)
    try:
        internal, custodian = client.trades_for_date(request.trade_date)
    except TradeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not internal and not custodian:
        raise HTTPException(status_code=404, detail=f"No trades found for {request.trade_date.isoformat()}")
    result = reconcile(internal, custodian, PRICE_TOLERANCE_BPS)
    return service.save_run(db, request.trade_date, result, PRICE_TOLERANCE_BPS, started_at)


@router.get("/runs", response_model=list[RunOut])
def get_runs(limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)):
    return service.list_runs(db, limit)


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    return _require_run(db, run_id)


@router.get("/runs/{run_id}/breaks", response_model=list[BreakOut])
def get_breaks(
    run_id: int,
    status: BreakStatus | None = None,
    break_type: BreakType | None = None,
    db: Session = Depends(get_db),
):
    _require_run(db, run_id)
    return service.list_breaks(db, run_id, status, break_type.value if break_type else None)


@router.get("/runs/{run_id}/breaks.csv")
def export_breaks(run_id: int, db: Session = Depends(get_db)):
    run = _require_run(db, run_id)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS)
    writer.writeheader()
    for item in service.list_breaks(db, run_id, None, None):
        writer.writerow({column: getattr(item, column) if getattr(item, column) is not None else "" for column in EXPORT_COLUMNS})
    filename = f"breaks_run{run.id}_{run.trade_date.isoformat()}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/breaks/{break_id}", response_model=BreakOut)
def patch_break(break_id: int, update: BreakUpdate, db: Session = Depends(get_db)):
    item = service.update_break(db, break_id, update)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Break {break_id} not found")
    return item


@router.get("/summary", response_model=Summary)
def get_summary(db: Session = Depends(get_db)):
    return service.summary(db)
