from datetime import date
from decimal import Decimal

import pytest

from app.engine import BreakType, price_difference_bps, reconcile
from tests.helpers import load_sample, trade


def types(result):
    return [b.break_type for b in result.breaks]


def test_identical_trades_match():
    result = reconcile([trade("A"), trade("B")], [trade("A"), trade("B")])
    assert result.matched_refs == ["A", "B"]
    assert result.breaks == []
    assert result.match_rate == Decimal("100.00")
    assert result.total_exposure == Decimal("0.00")


def test_missing_in_custodian_and_internal_with_notional_exposure():
    result = reconcile([trade("A"), trade("B")], [trade("A"), trade("C", quantity=Decimal("50"))])
    assert types(result) == [BreakType.MISSING_IN_CUSTODIAN, BreakType.MISSING_IN_INTERNAL]
    missing_custodian, missing_internal = result.breaks
    assert missing_custodian.trade_ref == "B"
    assert missing_custodian.exposure == Decimal("20000.00")
    assert missing_custodian.internal_value == "BUY 100 US0378331005 @ 200"
    assert missing_custodian.custodian_value is None
    assert missing_internal.trade_ref == "C"
    assert missing_internal.exposure == Decimal("10000.00")
    assert missing_internal.internal_value is None


def test_quantity_mismatch_exposure_uses_quantity_difference():
    result = reconcile([trade("A")], [trade("A", quantity=Decimal("90"))])
    (item,) = result.breaks
    assert item.break_type == BreakType.QUANTITY_MISMATCH
    assert (item.internal_value, item.custodian_value) == ("100", "90")
    assert item.exposure == Decimal("2000.00")


@pytest.mark.parametrize(
    "custodian_price, is_break",
    [
        (Decimal("200.00"), False),
        (Decimal("200.0199"), False),
        (Decimal("200.02"), False),
        (Decimal("200.0201"), True),
        (Decimal("199.50"), True),
    ],
)
def test_price_tolerance_in_basis_points(custodian_price, is_break):
    result = reconcile([trade("A")], [trade("A", price=custodian_price)], price_tolerance_bps=Decimal("1"))
    assert (BreakType.PRICE_MISMATCH in types(result)) is is_break


def test_price_mismatch_exposure():
    result = reconcile([trade("A")], [trade("A", price=Decimal("199.50"))])
    assert result.breaks[0].exposure == Decimal("50.00")


def test_price_difference_bps():
    assert price_difference_bps(Decimal("100"), Decimal("101")) == Decimal("100")


def test_side_mismatch_counts_double_notional():
    result = reconcile([trade("A")], [trade("A", side="SELL")])
    assert types(result) == [BreakType.SIDE_MISMATCH]
    assert result.breaks[0].exposure == Decimal("40000.00")


def test_multiple_field_breaks_on_one_trade_count_as_one_unmatched_ref():
    custodian = trade(
        "A",
        instrument="US5949181045",
        currency="EUR",
        settlement_date=date(2026, 10, 16),
        counterparty="Barclays",
    )
    result = reconcile([trade("A"), trade("B")], [custodian, trade("B")])
    assert set(types(result)) == {
        BreakType.INSTRUMENT_MISMATCH,
        BreakType.CURRENCY_MISMATCH,
        BreakType.SETTLEMENT_DATE_MISMATCH,
        BreakType.COUNTERPARTY_MISMATCH,
    }
    assert result.total_refs == 2
    assert result.match_rate == Decimal("50.00")


def test_counterparty_comparison_ignores_case_and_spaces():
    result = reconcile([trade("A")], [trade("A", counterparty="  goldman sachs ")])
    assert result.breaks == []


def test_empty_inputs():
    result = reconcile([], [])
    assert result.match_rate == Decimal("0.00")
    assert result.total_refs == 0


def test_sample_data_produces_expected_breaks():
    trade_date = date(2026, 10, 14)
    internal = load_sample("internal_trades.csv", trade_date)
    custodian = load_sample("custodian_trades.csv", trade_date)
    result = reconcile(internal, custodian, Decimal("1"))

    by_ref = {b.trade_ref: b.break_type for b in result.breaks}
    assert by_ref == {
        "TRD-20261014-0004": BreakType.QUANTITY_MISMATCH,
        "TRD-20261014-0007": BreakType.PRICE_MISMATCH,
        "TRD-20261014-0009": BreakType.MISSING_IN_CUSTODIAN,
        "TRD-20261014-0011": BreakType.QUANTITY_MISMATCH,
        "TRD-20261014-0019": BreakType.PRICE_MISMATCH,
        "TRD-20261014-0023": BreakType.SIDE_MISMATCH,
        "TRD-20261014-0027": BreakType.SETTLEMENT_DATE_MISMATCH,
        "TRD-20261014-0031": BreakType.COUNTERPARTY_MISMATCH,
        "TRD-20261014-0034": BreakType.MISSING_IN_CUSTODIAN,
        "TRD-20261014-9001": BreakType.MISSING_IN_INTERNAL,
    }
    assert "TRD-20261014-0015" in result.matched_refs
    assert (result.internal_count, result.custodian_count) == (40, 39)
    assert len(result.matched_refs) == 31
    assert result.match_rate == Decimal("75.61")
