import os
from decimal import Decimal


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = normalize_database_url(
    os.getenv("DATABASE_URL", "postgresql+psycopg://recon:recon@localhost:5432/recon_db")
)

TRADE_SERVICE_URL = os.getenv("TRADE_SERVICE_URL", "http://localhost:8001").rstrip("/")

TRADE_SERVICE_TIMEOUT_SECONDS = float(os.getenv("TRADE_SERVICE_TIMEOUT_SECONDS", "10"))

PRICE_TOLERANCE_BPS = Decimal(os.getenv("PRICE_TOLERANCE_BPS", "1"))

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
