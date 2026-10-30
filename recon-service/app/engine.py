from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

TWO_PLACES = Decimal("0.01")
BPS = Decimal("10000")


class BreakType(str, Enum):
    MISSING_IN_CUSTODIAN = "MISSING_IN_CUSTODIAN"
    MISSING_IN_INTERNAL = "MISSING_IN_INTERNAL"
    INSTRUMENT_MISMATCH = "INSTRUMENT_MISMATCH"
    SIDE_MISMATCH = "SIDE_MISMATCH"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"
    PRICE_MISMATCH = "PRICE_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    SETTLEMENT_DATE_MISMATCH = "SETTLEMENT_DATE_MISMATCH"
    COUNTERPARTY_MISMATCH = "COUNTERPARTY_MISMATCH"


@dataclass(frozen=True)
class TradeRecord:
    trade_ref: str
    trade_date: date
    settlement_date: date
    instrument: str
    side: str
    quantity: Decimal
    price: Decimal
    currency: str
    counterparty: str

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.price


@dataclass(frozen=True)
class BreakRecord:
    trade_ref: str
    break_type: BreakType
    field: str | None
    internal_value: str | None
    custodian_value: str | None
    exposure: Decimal
    instrument: str
    counterparty: str


@dataclass
class ReconResult:
    internal_count: int
    custodian_count: int
    matched_refs: list[str] = field(default_factory=list)
    breaks: list[BreakRecord] = field(default_factory=list)

    @property
    def total_refs(self) -> int:
        return len(self.matched_refs) + len({b.trade_ref for b in self.breaks})

    @property
    def match_rate(self) -> Decimal:
        if self.total_refs == 0:
            return Decimal("0.00")
        return (Decimal(len(self.matched_refs)) * 100 / Decimal(self.total_refs)).quantize(TWO_PLACES, ROUND_HALF_UP)

    @property
    def total_exposure(self) -> Decimal:
        return sum((b.exposure for b in self.breaks), Decimal("0.00")).quantize(TWO_PLACES, ROUND_HALF_UP)


def _money(value: Decimal) -> Decimal:
    return value.copy_abs().quantize(TWO_PLACES, ROUND_HALF_UP)


def _text(value) -> str:
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return str(value)


def price_difference_bps(internal_price: Decimal, custodian_price: Decimal) -> Decimal:
    return (internal_price - custodian_price).copy_abs() / internal_price * BPS


def compare_pair(internal: TradeRecord, custodian: TradeRecord, price_tolerance_bps: Decimal) -> list[BreakRecord]:
    breaks: list[BreakRecord] = []

    def add(break_type: BreakType, field_name: str, exposure: Decimal) -> None:
        breaks.append(
            BreakRecord(
                trade_ref=internal.trade_ref,
                break_type=break_type,
                field=field_name,
                internal_value=_text(getattr(internal, field_name)),
                custodian_value=_text(getattr(custodian, field_name)),
                exposure=_money(exposure),
                instrument=internal.instrument,
                counterparty=internal.counterparty,
            )
        )

    if internal.instrument != custodian.instrument:
        add(BreakType.INSTRUMENT_MISMATCH, "instrument", internal.notional)
    if internal.side != custodian.side:
        add(BreakType.SIDE_MISMATCH, "side", internal.notional * 2)
    if internal.quantity != custodian.quantity:
        add(BreakType.QUANTITY_MISMATCH, "quantity", (internal.quantity - custodian.quantity) * internal.price)
    if price_difference_bps(internal.price, custodian.price) > price_tolerance_bps:
        add(BreakType.PRICE_MISMATCH, "price", (internal.price - custodian.price) * internal.quantity)
    if internal.currency != custodian.currency:
        add(BreakType.CURRENCY_MISMATCH, "currency", internal.notional)
    if internal.settlement_date != custodian.settlement_date:
        add(BreakType.SETTLEMENT_DATE_MISMATCH, "settlement_date", internal.notional)
    if internal.counterparty.strip().casefold() != custodian.counterparty.strip().casefold():
        add(BreakType.COUNTERPARTY_MISMATCH, "counterparty", internal.notional)
    return breaks


def _missing(trade: TradeRecord, break_type: BreakType) -> BreakRecord:
    present_internal = break_type == BreakType.MISSING_IN_CUSTODIAN
    summary = f"{trade.side} {_text(trade.quantity)} {trade.instrument} @ {_text(trade.price)}"
    return BreakRecord(
        trade_ref=trade.trade_ref,
        break_type=break_type,
        field=None,
        internal_value=summary if present_internal else None,
        custodian_value=None if present_internal else summary,
        exposure=_money(trade.notional),
        instrument=trade.instrument,
        counterparty=trade.counterparty,
    )


def reconcile(
    internal_trades: list[TradeRecord],
    custodian_trades: list[TradeRecord],
    price_tolerance_bps: Decimal = Decimal("1"),
) -> ReconResult:
    internal_by_ref = {t.trade_ref: t for t in internal_trades}
    custodian_by_ref = {t.trade_ref: t for t in custodian_trades}
    result = ReconResult(internal_count=len(internal_by_ref), custodian_count=len(custodian_by_ref))

    for ref in sorted(internal_by_ref.keys() | custodian_by_ref.keys()):
        internal = internal_by_ref.get(ref)
        custodian = custodian_by_ref.get(ref)
        if custodian is None:
            result.breaks.append(_missing(internal, BreakType.MISSING_IN_CUSTODIAN))
        elif internal is None:
            result.breaks.append(_missing(custodian, BreakType.MISSING_IN_INTERNAL))
        else:
            pair_breaks = compare_pair(internal, custodian, price_tolerance_bps)
            if pair_breaks:
                result.breaks.extend(pair_breaks)
            else:
                result.matched_refs.append(ref)
    return result
