from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.engine import BreakType


class BreakStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class RunRequest(BaseModel):
    trade_date: date


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_date: date
    status: str
    internal_count: int
    custodian_count: int
    matched_count: int
    break_count: int
    match_rate: Decimal
    total_exposure: Decimal
    price_tolerance_bps: Decimal
    started_at: datetime
    completed_at: datetime


class BreakOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    trade_ref: str
    break_type: BreakType
    field: str | None
    internal_value: str | None
    custodian_value: str | None
    exposure: Decimal
    instrument: str
    counterparty: str
    status: BreakStatus
    resolution_comment: str | None
    resolved_by: str | None
    resolved_at: datetime | None


class BreakUpdate(BaseModel):
    status: BreakStatus
    comment: str | None = Field(default=None, max_length=1000)
    resolved_by: str | None = Field(default=None, max_length=64)

    @field_validator("comment", "resolved_by", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def require_comment_when_resolving(self):
        if self.status == BreakStatus.RESOLVED and not self.comment:
            raise ValueError("A comment is required to resolve a break")
        return self


class BreakTypeSummary(BaseModel):
    break_type: BreakType
    count: int
    exposure: Decimal


class Summary(BaseModel):
    total_runs: int
    dates_reconciled: int
    open_breaks: int
    resolved_breaks: int
    open_exposure: Decimal
    latest_run: RunOut | None
    open_breaks_by_type: list[BreakTypeSummary]
