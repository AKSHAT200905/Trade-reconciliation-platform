from decimal import Decimal

import pytest

from app.csv_parser import CsvFormatError, parse_trades_csv

HEADER = "trade_ref,trade_date,settlement_date,instrument,side,quantity,price,currency,counterparty\n"


def test_parses_valid_rows_and_normalizes_values():
    content = (HEADER + "T-1,2026-10-14,2026-10-15,us0378331005, buy ,100,228.5,usd,Goldman Sachs\n").encode()
    valid, rejected = parse_trades_csv(content)
    assert rejected == []
    row, trade = valid[0]
    assert row == 2
    assert trade.instrument == "US0378331005"
    assert trade.side.value == "BUY"
    assert trade.currency == "USD"
    assert trade.quantity == Decimal("100")


def test_handles_byte_order_mark_and_blank_lines():
    content = ("﻿" + HEADER + "T-1,2026-10-14,2026-10-15,X1,SELL,5,10,USD,Citi\n\n,,,,,,,,\n").encode("utf-8")
    valid, rejected = parse_trades_csv(content)
    assert len(valid) == 1
    assert rejected == []


def test_rejects_bad_rows_with_reasons():
    content = (
        HEADER
        + "T-1,2026-10-14,2026-10-15,X1,HOLD,100,10,USD,Citi\n"
        + "T-2,2026-10-14,2026-10-15,X1,BUY,-5,10,USD,Citi\n"
        + "T-3,2026-10-14,2026-10-13,X1,BUY,5,10,USD,Citi\n"
        + "T-4,not-a-date,2026-10-15,X1,BUY,5,10,USD,Citi\n"
        + "T-5,2026-10-14,2026-10-15,X1,BUY,5,10,USD,Citi\n"
        + "T-5,2026-10-14,2026-10-15,X1,BUY,5,10,USD,Citi\n"
    ).encode()
    valid, rejected = parse_trades_csv(content)
    assert [t.trade_ref for _, t in valid] == ["T-5"]
    reasons = {r.trade_ref: r.error for r in rejected}
    assert "side" in reasons["T-1"]
    assert "quantity" in reasons["T-2"]
    assert "settlement_date cannot be before trade_date" in reasons["T-3"]
    assert "trade_date" in reasons["T-4"]
    assert reasons["T-5"] == "Duplicate trade_ref in file"
    assert [r.row for r in rejected] == [2, 3, 4, 5, 7]


def test_missing_columns_raise_format_error():
    with pytest.raises(CsvFormatError, match="Missing required columns: price"):
        parse_trades_csv(b"trade_ref,trade_date,settlement_date,instrument,side,quantity,currency,counterparty\n")


def test_empty_file_raises_format_error():
    with pytest.raises(CsvFormatError, match="empty"):
        parse_trades_csv(b"   ")


def test_non_utf8_file_raises_format_error():
    with pytest.raises(CsvFormatError, match="UTF-8"):
        parse_trades_csv(b"\xff\xfe\x00\x00bad")
