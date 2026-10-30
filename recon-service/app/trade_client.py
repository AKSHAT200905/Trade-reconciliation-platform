from datetime import date
from decimal import Decimal

import httpx

from app.config import TRADE_SERVICE_TIMEOUT_SECONDS, TRADE_SERVICE_URL
from app.engine import TradeRecord


class TradeServiceError(RuntimeError):
    pass


def to_record(item: dict) -> TradeRecord:
    return TradeRecord(
        trade_ref=item["trade_ref"],
        trade_date=date.fromisoformat(item["trade_date"]),
        settlement_date=date.fromisoformat(item["settlement_date"]),
        instrument=item["instrument"],
        side=item["side"],
        quantity=Decimal(str(item["quantity"])),
        price=Decimal(str(item["price"])),
        currency=item["currency"],
        counterparty=item["counterparty"],
    )


class TradeServiceClient:
    def __init__(self, base_url: str = TRADE_SERVICE_URL, timeout: float = TRADE_SERVICE_TIMEOUT_SECONDS):
        self.base_url = base_url
        self.timeout = timeout

    def trades_for_date(self, trade_date: date) -> tuple[list[TradeRecord], list[TradeRecord]]:
        url = f"{self.base_url}/api/trades/by-date/{trade_date.isoformat()}"
        try:
            response = httpx.get(url, timeout=self.timeout)
            response.raise_for_status()
            items = response.json()
        except httpx.HTTPError as exc:
            raise TradeServiceError(f"Could not fetch trades from trade-service: {exc}") from exc
        internal = [to_record(i) for i in items if i["source"] == "INTERNAL"]
        custodian = [to_record(i) for i in items if i["source"] == "CUSTODIAN"]
        return internal, custodian


def get_trade_client() -> TradeServiceClient:
    return TradeServiceClient()
