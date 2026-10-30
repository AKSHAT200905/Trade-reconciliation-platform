# TradeRecon: Trade Reconciliation Platform

TradeRecon is a full-stack, microservices platform that reconciles trades between a financial firm's **internal trading desk** and its **custodian bank**. It ingests trade files from both sides, matches them field by field, flags every mismatch ("break"), measures the money at risk, and gives operations analysts a dashboard to investigate and resolve breaks with a full audit trail.

Trade reconciliation is a daily control at banks, brokers, asset managers and hedge funds. If a trade is booked differently by the firm and by its custodian, positions, cash and P&L are wrong until someone fixes it. This project automates that check.

![CI/CD](https://github.com/AKSHAT200905/trade-recon-platform/actions/workflows/ci.yml/badge.svg)

![Dashboard](docs/dashboard.png)

## Features

- **Two microservices** with their own databases, talking over REST
  - **trade-service** ingests CSV trade files from each source, validates every row, upserts by trade reference and reports rejected rows with reasons
  - **recon-service** pulls both sides for a trade date, runs the matching engine, stores the run and its breaks, and manages the resolution workflow
- **Matching engine** that detects 9 break types, applies a configurable price tolerance in basis points, and computes the dollar exposure of every break
- **Break workflow**: resolve with a mandatory comment and analyst name, reopen if needed, export breaks to CSV
- **Dashboard**: open breaks, open exposure, latest match rate, breaks by type, run history
- **PostgreSQL** with versioned **Alembic** migrations, unique and check constraints, and indexes
- **43 automated tests** (pytest + Vitest), run against real PostgreSQL in CI
- **Docker Compose** brings up the whole stack with one command
- **GitHub Actions CI/CD**: tests, migration check, end-to-end smoke test of the running stack, then publishes Docker images to GitHub Container Registry

## Architecture

```mermaid
flowchart LR
    U[Ops analyst<br/>browser] --> F[React dashboard<br/>served by nginx]
    F -- /api/trades --> T[trade-service<br/>FastAPI]
    F -- /api/recon --> R[recon-service<br/>FastAPI]
    R -- REST: trades for a date --> T
    T --> TDB[(PostgreSQL<br/>trades_db)]
    R --> RDB[(PostgreSQL<br/>recon_db)]
```

Each service owns its data (database-per-service). The recon-service never reads the trades table directly; it asks trade-service over HTTP. nginx serves the built React app and routes API calls to the right service, so the browser only ever talks to one origin.

## Screenshots

**Breaks: investigate, resolve with a comment, export**

![Breaks](docs/breaks.png)

**Trades: upload CSVs per source, see rejected rows, search and filter**

![Trades](docs/trades.png)

## Tech stack

| Layer | Technology |
|---|---|
| Backend services | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, httpx |
| Database | PostgreSQL 16, Alembic migrations |
| Frontend | React 19, Vite, plain CSS |
| Testing | pytest, FastAPI TestClient, Vitest |
| Containers | Docker, Docker Compose, nginx |
| CI/CD | GitHub Actions, GitHub Container Registry |

## Break types

| Break type | Meaning | Exposure counted |
|---|---|---|
| Missing in custodian | Internal booked it, custodian has no record | Full notional |
| Missing in internal | Custodian has a trade the desk never booked | Full notional |
| Instrument mismatch | Different ISIN | Full notional |
| Side mismatch | One side says BUY, the other SELL | 2 × notional (position is wrong both ways) |
| Quantity mismatch | Different number of shares | Quantity difference × price |
| Price mismatch | Price differs by more than the tolerance (default 1 bp) | Price difference × quantity |
| Currency mismatch | Different currency | Full notional |
| Settlement date mismatch | Settles on a different day | Full notional |
| Counterparty mismatch | Different broker (case and spaces ignored) | Full notional |

A trade matches only when every field agrees. Match rate = matched trade references ÷ all trade references seen on either side.

## Run it with one command (easiest)

You need Python 3.10+ and Node.js 20+. From the project folder:

```bash
python run.py
```

The first run installs everything (a few minutes). After that it starts in seconds. It creates the databases, starts both services and the dashboard, and opens **http://localhost:5173** in your browser. Press `Ctrl+C` to stop everything.

```bash
python run.py --reset
```

starts again with empty databases.

## Run it with Docker

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.

```bash
docker compose up --build
```

Then open **http://localhost:3000**.

1. Click **Load sample data** on the Dashboard (80 internal and 78 custodian trades across two days, with deliberate breaks).
2. Click **Reconcile** next to a trade date.
3. Open **Breaks**, resolve a few with a comment, try the filters and **Export CSV**.
4. On **Trades**, upload your own CSV files.

API docs (Swagger UI): http://localhost:8001/docs and http://localhost:8002/docs

Stop with `Ctrl+C`, and run `docker compose down -v` to also delete the database.

## Run it without Docker (Windows, quick start)

This uses SQLite files instead of PostgreSQL so you only need Python 3.12+ and Node.js 22+. Open three PowerShell windows in the project folder.

**Window 1: trade-service**
```powershell
cd trade-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:DATABASE_URL = "sqlite:///./trades.db"
alembic upgrade head
uvicorn app.main:app --port 8001
```

**Window 2: recon-service**
```powershell
cd recon-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:DATABASE_URL = "sqlite:///./recon.db"
$env:TRADE_SERVICE_URL = "http://localhost:8001"
alembic upgrade head
uvicorn app.main:app --port 8002
```

**Window 3: frontend**
```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. On macOS or Linux use `source .venv/bin/activate` and `export DATABASE_URL=...` instead.

To use PostgreSQL instead of SQLite, set `DATABASE_URL` to something like `postgresql://recon:recon@localhost:5432/trades_db`.

## Tests

```bash
cd trade-service && pytest
cd recon-service && pytest
cd frontend && npm test
```

Backend tests run on a temporary SQLite file by default. Set `TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/test_db` to run them against PostgreSQL, which is what CI does.

## API

**trade-service** (port 8001)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/trades/upload` | Upload a CSV (`source` = INTERNAL or CUSTODIAN) |
| POST | `/api/trades?source=` | Create or update one trade from JSON |
| POST | `/api/trades/sample` | Load the bundled sample data |
| GET | `/api/trades` | List trades with `source`, `trade_date`, `search`, `limit`, `offset` |
| GET | `/api/trades/by-date/{date}` | All trades for one date (used by recon-service) |
| GET | `/api/trades/dates` | Trade counts per date and source |
| DELETE | `/api/trades` | Delete trades, optionally for one `trade_date` |

**recon-service** (port 8002)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/recon/runs` | Reconcile a trade date |
| GET | `/api/recon/runs` | Run history |
| GET | `/api/recon/runs/{id}` | One run |
| GET | `/api/recon/runs/{id}/breaks` | Breaks, filter by `status` and `break_type` |
| GET | `/api/recon/runs/{id}/breaks.csv` | Export breaks |
| PATCH | `/api/recon/breaks/{id}` | Resolve (comment required) or reopen |
| GET | `/api/recon/summary` | Dashboard numbers, latest run per date |

Both services also expose `GET /health`.

## CSV format

```csv
trade_ref,trade_date,settlement_date,instrument,side,quantity,price,currency,counterparty
TRD-20261014-0001,2026-10-14,2026-10-15,US0378331005,BUY,500,228.4000,USD,Goldman Sachs
```

Rows are validated individually: bad dates, non-positive quantity or price, unknown side, settlement before trade date and duplicate references inside a file are rejected with the row number and reason, while valid rows are still saved. Re-uploading the same `trade_ref` for the same source updates it instead of duplicating it.

## Configuration

| Variable | Service | Default |
|---|---|---|
| `DATABASE_URL` | both | local PostgreSQL URL |
| `TRADE_SERVICE_URL` | recon-service, frontend container | `http://localhost:8001` |
| `RECON_SERVICE_URL` | frontend container | `http://recon-service:8002` |
| `PRICE_TOLERANCE_BPS` | recon-service | `1` |
| `CORS_ORIGINS` | both | `*` |
| `PORT` | all containers | 8001, 8002, 80 |

## CI/CD pipeline

On every push and pull request, GitHub Actions:

1. Tests both services against a real PostgreSQL 16 container, after checking that migrations apply and roll back cleanly
2. Tests and builds the React app
3. Builds all images, starts the full stack with Docker Compose, loads sample data through nginx, reconciles a date and checks the exact result
4. On `main`, pushes the three images to `ghcr.io/<your-username>/traderecon-*`

## Deploy it live (Render, free tier)

1. Push this repository to GitHub.
2. On [render.com](https://render.com), create a **PostgreSQL** database and copy its **Internal Database URL**.
3. Create a **Web Service** from the repo, root directory `trade-service`, runtime Docker. Set `DATABASE_URL` to the database URL.
4. Create a second Web Service, root directory `recon-service`, runtime Docker. Set `DATABASE_URL` to the same database URL and `TRADE_SERVICE_URL` to the trade-service's public `https://...onrender.com` URL. Both services can share one database because their tables and migration history tables have different names.
5. Create a third Web Service, root directory `frontend`, runtime Docker. Set `TRADE_SERVICE_URL` and `RECON_SERVICE_URL` to the two public service URLs.
6. Open the frontend's URL. Free Render services sleep when idle, so the first request after a pause can take up to a minute.

## Project structure

```
trade-recon-platform/
├── trade-service/          FastAPI service: ingestion, validation, trade API
│   ├── app/                routes, service layer, models, CSV parser, sample data
│   ├── alembic/            database migrations
│   └── tests/
├── recon-service/          FastAPI service: matching engine, runs, breaks
│   ├── app/                engine, routes, service layer, models, trade-service client
│   ├── alembic/
│   └── tests/
├── frontend/               React + Vite dashboard, nginx config
├── sample-data/            the same sample CSVs, for manual uploads
├── scripts/                sample data generator
├── infra/                  PostgreSQL init script
├── docker-compose.yml
└── .github/workflows/      CI/CD pipeline
```

## Design decisions

- **Database per service**: recon-service cannot couple itself to the trades table; it only depends on trade-service's API contract.
- **Every run is stored, never overwritten**: re-reconciling a date creates a new run, so there is an audit trail. The dashboard uses the latest run per date.
- **Decimal everywhere for money**: quantities and prices use `NUMERIC` in PostgreSQL and `Decimal` in Python, never floats.
- **Price tolerance in basis points**: tiny rounding differences between systems are normal, so 1 bp is the default and configurable.
- **Partial uploads succeed**: one bad row does not reject a whole file of good trades; the analyst sees exactly which rows failed and why.

## Possible extensions

- Kafka events from trade-service so reconciliation runs automatically when both sides arrive
- Fuzzy matching for trades with different references but identical economics
- Authentication and role-based access for analysts and supervisors
- Ageing of open breaks and email alerts for breaks above an exposure threshold
