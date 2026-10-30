import csv
import io

from pydantic import ValidationError

from app.schemas import RejectedRow, TradeIn

REQUIRED_COLUMNS = [
    "trade_ref",
    "trade_date",
    "settlement_date",
    "instrument",
    "side",
    "quantity",
    "price",
    "currency",
    "counterparty",
]


class CsvFormatError(ValueError):
    pass


def _format_validation_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err.get("loc", ()))
        message = err.get("msg", "invalid value").removeprefix("Value error, ")
        parts.append(f"{field}: {message}" if field else message)
    return "; ".join(parts)


def parse_trades_csv(content: bytes) -> tuple[list[tuple[int, TradeIn]], list[RejectedRow]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvFormatError("File must be UTF-8 encoded CSV") from exc

    if not text.strip():
        raise CsvFormatError("File is empty")

    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise CsvFormatError(f"Missing required columns: {', '.join(missing)}")

    valid: list[tuple[int, TradeIn]] = []
    rejected: list[RejectedRow] = []
    seen_refs: set[str] = set()

    for row_number, raw in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items() if k is not None}
        if not any(row.get(c) for c in REQUIRED_COLUMNS):
            continue
        ref = row.get("trade_ref") or None
        try:
            trade = TradeIn(**{c: row.get(c) for c in REQUIRED_COLUMNS})
        except ValidationError as exc:
            rejected.append(RejectedRow(row=row_number, trade_ref=ref, error=_format_validation_error(exc)))
            continue
        if trade.trade_ref in seen_refs:
            rejected.append(RejectedRow(row=row_number, trade_ref=ref, error="Duplicate trade_ref in file"))
            continue
        seen_refs.add(trade.trade_ref)
        valid.append((row_number, trade))

    return valid, rejected
