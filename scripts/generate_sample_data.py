import csv
import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = [ROOT / "sample-data", ROOT / "trade-service" / "app" / "data"]

INSTRUMENTS = [
    ("US0378331005", Decimal("228.40")),
    ("US5949181045", Decimal("415.20")),
    ("US0231351067", Decimal("186.75")),
    ("US02079K3059", Decimal("165.10")),
    ("US67066G1040", Decimal("118.90")),
    ("US46625H1005", Decimal("221.35")),
    ("US38141G1040", Decimal("512.60")),
    ("US0846707026", Decimal("458.15")),
    ("US92826C8394", Decimal("289.40")),
    ("US30231G1022", Decimal("117.85")),
]
COUNTERPARTIES = ["Goldman Sachs", "JP Morgan", "Morgan Stanley", "Citigroup", "Barclays", "BNP Paribas"]
COLUMNS = ["trade_ref", "trade_date", "settlement_date", "instrument", "side", "quantity", "price", "currency", "counterparty"]


def business_days_after(start: date, days: int) -> date:
    current = start
    while days > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days -= 1
    return current


def money(value: Decimal, places: str) -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def build_internal(rng: random.Random, trade_date: date, prefix: str, count: int) -> list[dict]:
    rows = []
    for n in range(1, count + 1):
        isin, base = rng.choice(INSTRUMENTS)
        price = money(base * Decimal(str(1 + rng.uniform(-0.02, 0.02))), "0.0001")
        rows.append({
            "trade_ref": f"{prefix}-{n:04d}",
            "trade_date": trade_date.isoformat(),
            "settlement_date": business_days_after(trade_date, 1).isoformat(),
            "instrument": isin,
            "side": rng.choice(["BUY", "SELL"]),
            "quantity": str(rng.choice([100, 250, 500, 750, 1000, 1500, 2000, 5000])),
            "price": str(price),
            "currency": "USD",
            "counterparty": rng.choice(COUNTERPARTIES),
        })
    return rows


def build_custodian(internal: list[dict], trade_date: date, prefix: str) -> list[dict]:
    custodian = [dict(r) for r in internal]
    by_ref = {r["trade_ref"]: r for r in custodian}

    by_ref[f"{prefix}-0004"]["quantity"] = str(int(by_ref[f"{prefix}-0004"]["quantity"]) - 100)
    by_ref[f"{prefix}-0011"]["quantity"] = str(int(by_ref[f"{prefix}-0011"]["quantity"]) + 250)
    by_ref[f"{prefix}-0007"]["price"] = str(money(Decimal(by_ref[f"{prefix}-0007"]["price"]) * Decimal("1.0125"), "0.0001"))
    by_ref[f"{prefix}-0019"]["price"] = str(money(Decimal(by_ref[f"{prefix}-0019"]["price"]) - Decimal("0.50"), "0.0001"))
    by_ref[f"{prefix}-0015"]["price"] = str(money(Decimal(by_ref[f"{prefix}-0015"]["price"]) + Decimal("0.0001"), "0.0001"))
    by_ref[f"{prefix}-0023"]["side"] = "SELL" if by_ref[f"{prefix}-0023"]["side"] == "BUY" else "BUY"
    by_ref[f"{prefix}-0027"]["settlement_date"] = business_days_after(trade_date, 2).isoformat()
    by_ref[f"{prefix}-0031"]["counterparty"] = "Deutsche Bank"

    removed = {f"{prefix}-0009", f"{prefix}-0034"}
    custodian = [r for r in custodian if r["trade_ref"] not in removed]
    custodian.append({
        "trade_ref": f"{prefix}-9001",
        "trade_date": trade_date.isoformat(),
        "settlement_date": business_days_after(trade_date, 1).isoformat(),
        "instrument": "US0378331005",
        "side": "BUY",
        "quantity": "300",
        "price": "229.1500",
        "currency": "USD",
        "counterparty": "Goldman Sachs",
    })
    return custodian


def write(rows: list[dict], name: str) -> None:
    for folder in OUTPUTS:
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / name, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    rng = random.Random(2026)
    internal_all, custodian_all = [], []
    for trade_date, prefix in [(date(2026, 10, 13), "TRD-20261013"), (date(2026, 10, 14), "TRD-20261014")]:
        internal = build_internal(rng, trade_date, prefix, 40)
        internal_all += internal
        custodian_all += build_custodian(internal, trade_date, prefix)
    write(internal_all, "internal_trades.csv")
    write(custodian_all, "custodian_trades.csv")
    print(f"internal rows: {len(internal_all)}, custodian rows: {len(custodian_all)}")


if __name__ == "__main__":
    main()
