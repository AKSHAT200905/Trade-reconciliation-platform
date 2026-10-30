from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Source(str, Enum):
    INTERNAL = "INTERNAL"
    CUSTODIAN = "CUSTODIAN"


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeIn(BaseModel):
    trade_ref: str = Field(min_length=1, max_length=64)
    trade_date: date
    settlement_date: date
    instrument: str = Field(min_length=1, max_length=32)
    side: Side
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    price: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    currency: str = Field(min_length=3, max_length=3)
    counterparty: str = Field(min_length=1, max_length=128)

    @field_validator("trade_ref", "instrument", "counterparty", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("side", mode="before")
    @classmethod
    def upper_side(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("currency", "instrument", mode="after")
    @classmethod
    def upper_codes(cls, value):
        return value.upper()

    @model_validator(mode="after")
    def check_dates(self):
        if self.settlement_date < self.trade_date:
            raise ValueError("settlement_date cannot be before trade_date")
        return self


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_ref: str
    source: Source
    trade_date: date
    settlement_date: date
    instrument: str
    side: Side
    quantity: Decimal
    price: Decimal
    currency: str
    counterparty: str


class TradePage(BaseModel):
    total: int
    items: list[TradeOut]


class RejectedRow(BaseModel):
    row: int
    trade_ref: str | None
    error: str


class UploadResult(BaseModel):
    source: Source
    inserted: int
    updated: int
    rejected: list[RejectedRow]


class TradeDateSummary(BaseModel):
    trade_date: date
    internal_count: int
    custodian_count: int
