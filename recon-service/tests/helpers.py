import csv
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.engine import TradeRecord

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample-data"


def trade(ref="T-1", **overrides) -> TradeRecord:
    base = TradeRecord(
        trade_ref=ref,
        trade_date=date(2026, 10, 14),
        settlement_date=date(2026, 10, 15),
        instrument="US0378331005",
        side="BUY",
        quantity=Decimal("100"),
        price=Decimal("200.00"),
        currency="USD",
        counterparty="Goldman Sachs",
    )
    return replace(base, **overrides)


def load_sample(file_name: str, trade_date: date) -> list[TradeRecord]:
    with open(SAMPLE_DIR / file_name, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        TradeRecord(
            trade_ref=r["trade_ref"],
            trade_date=date.fromisoformat(r["trade_date"]),
            settlement_date=date.fromisoformat(r["settlement_date"]),
            instrument=r["instrument"],
            side=r["side"],
            quantity=Decimal(r["quantity"]),
            price=Decimal(r["price"]),
            currency=r["currency"],
            counterparty=r["counterparty"],
        )
        for r in rows
        if r["trade_date"] == trade_date.isoformat()
    ]
