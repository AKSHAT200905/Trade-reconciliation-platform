from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import MAX_UPLOAD_BYTES
from app.csv_parser import CsvFormatError, parse_trades_csv
from app.db import get_db
from app.schemas import Source, TradeDateSummary, TradeIn, TradeOut, TradePage, UploadResult
from app import service

router = APIRouter(prefix="/api/trades", tags=["trades"])

SAMPLE_DIR = Path(__file__).parent / "data"
SAMPLE_FILES = {
    Source.INTERNAL: SAMPLE_DIR / "internal_trades.csv",
    Source.CUSTODIAN: SAMPLE_DIR / "custodian_trades.csv",
}


def _ingest(db: Session, source: Source, content: bytes) -> UploadResult:
    try:
        valid, rejected = parse_trades_csv(content)
    except CsvFormatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    inserted, updated = service.upsert_trades(db, source, [trade for _, trade in valid])
    return UploadResult(source=source, inserted=inserted, updated=updated, rejected=rejected)


@router.post("/upload", response_model=UploadResult)
async def upload_trades(
    source: Source = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than the upload limit")
    return _ingest(db, source, content)


@router.post("", response_model=TradeOut, status_code=201)
def create_trade(trade: TradeIn, source: Source = Query(...), db: Session = Depends(get_db)):
    service.upsert_trades(db, source, [trade])
    return TradeOut.model_validate(service.get_trade(db, source, trade.trade_ref))


@router.post("/sample", response_model=list[UploadResult])
def load_sample_data(db: Session = Depends(get_db)):
    return [_ingest(db, source, path.read_bytes()) for source, path in SAMPLE_FILES.items()]


@router.get("", response_model=TradePage)
def get_trades(
    source: Source | None = None,
    trade_date: date | None = None,
    search: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    total, items = service.list_trades(db, source, trade_date, search, limit, offset)
    return TradePage(total=total, items=[TradeOut.model_validate(t) for t in items])


@router.get("/by-date/{trade_date}", response_model=list[TradeOut])
def get_trades_for_date(trade_date: date, db: Session = Depends(get_db)):
    return [TradeOut.model_validate(t) for t in service.trades_for_date(db, trade_date)]


@router.get("/dates", response_model=list[TradeDateSummary])
def get_trade_dates(db: Session = Depends(get_db)):
    return [
        TradeDateSummary(trade_date=d, internal_count=i, custodian_count=c)
        for d, i, c in service.trade_date_summary(db)
    ]


@router.delete("")
def remove_trades(trade_date: date | None = None, db: Session = Depends(get_db)):
    return {"deleted": service.delete_trades(db, trade_date)}
