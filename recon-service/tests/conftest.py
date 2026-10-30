import os
import tempfile
from pathlib import Path

_db_file = Path(tempfile.gettempdir()) / "recon_service_test.db"
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", f"sqlite+pysqlite:///{_db_file}")

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.trade_client import TradeServiceError, get_trade_client


class FakeTradeClient:
    def __init__(self):
        self.trades: dict = {}
        self.fail = False

    def set_trades(self, trade_date, internal, custodian):
        self.trades[trade_date] = (internal, custodian)

    def trades_for_date(self, trade_date):
        if self.fail:
            raise TradeServiceError("Could not fetch trades from trade-service: connection refused")
        return self.trades.get(trade_date, ([], []))


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def fake_client():
    return FakeTradeClient()


@pytest.fixture
def client(fake_client):
    app.dependency_overrides[get_trade_client] = lambda: fake_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
