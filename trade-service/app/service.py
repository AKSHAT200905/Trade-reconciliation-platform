from datetime import date

from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session

from app.models import Trade
from app.schemas import Source, TradeIn

TRADE_FIELDS = (
    "trade_date",
    "settlement_date",
    "instrument",
    "side",
    "quantity",
    "price",
    "currency",
    "counterparty",
)


def _values(trade: TradeIn) -> dict:
    data = trade.model_dump()
    data["side"] = trade.side.value
    return {field: data[field] for field in TRADE_FIELDS}


def upsert_trades(db: Session, source: Source, trades: list[TradeIn]) -> tuple[int, int]:
    if not trades:
        return 0, 0
    refs = [t.trade_ref for t in trades]
    existing = {
        t.trade_ref: t
        for t in db.scalars(select(Trade).where(Trade.source == source.value, Trade.trade_ref.in_(refs)))
    }
    inserted = updated = 0
    for trade in trades:
        values = _values(trade)
        current = existing.get(trade.trade_ref)
        if current is None:
            db.add(Trade(trade_ref=trade.trade_ref, source=source.value, **values))
            inserted += 1
        else:
            for field, value in values.items():
                setattr(current, field, value)
            updated += 1
    db.commit()
    return inserted, updated


def get_trade(db: Session, source: Source, trade_ref: str) -> Trade | None:
    return db.scalar(select(Trade).where(Trade.source == source.value, Trade.trade_ref == trade_ref))


def list_trades(
    db: Session,
    source: Source | None,
    trade_date: date | None,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[int, list[Trade]]:
    query = select(Trade)
    if source is not None:
        query = query.where(Trade.source == source.value)
    if trade_date is not None:
        query = query.where(Trade.trade_date == trade_date)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            Trade.trade_ref.ilike(pattern) | Trade.instrument.ilike(pattern) | Trade.counterparty.ilike(pattern)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Trade.trade_date.desc(), Trade.trade_ref, Trade.source).limit(limit).offset(offset)).all()
    return total, list(items)


def trades_for_date(db: Session, trade_date: date) -> list[Trade]:
    return list(db.scalars(select(Trade).where(Trade.trade_date == trade_date).order_by(Trade.trade_ref, Trade.source)))


def trade_date_summary(db: Session) -> list[tuple[date, int, int]]:
    internal = func.sum(case((Trade.source == Source.INTERNAL.value, 1), else_=0))
    custodian = func.sum(case((Trade.source == Source.CUSTODIAN.value, 1), else_=0))
    rows = db.execute(
        select(Trade.trade_date, internal, custodian).group_by(Trade.trade_date).order_by(Trade.trade_date.desc())
    ).all()
    return [(row[0], int(row[1] or 0), int(row[2] or 0)) for row in rows]


def delete_trades(db: Session, trade_date: date | None) -> int:
    statement = delete(Trade)
    if trade_date is not None:
        statement = statement.where(Trade.trade_date == trade_date)
    result = db.execute(statement)
    db.commit()
    return result.rowcount or 0
