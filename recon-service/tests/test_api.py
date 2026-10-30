from datetime import date
from decimal import Decimal

from tests.helpers import load_sample, trade

DAY = date(2026, 10, 14)


def load_sample_day(fake_client, trade_date=DAY):
    fake_client.set_trades(
        trade_date,
        load_sample("internal_trades.csv", trade_date),
        load_sample("custodian_trades.csv", trade_date),
    )


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_run_reconciliation_and_read_back(client, fake_client):
    load_sample_day(fake_client)
    response = client.post("/api/recon/runs", json={"trade_date": "2026-10-14"})
    assert response.status_code == 201
    run = response.json()
    assert run["internal_count"] == 40
    assert run["custodian_count"] == 39
    assert run["matched_count"] == 31
    assert run["break_count"] == 10
    assert Decimal(run["match_rate"]) == Decimal("75.61")
    assert Decimal(run["total_exposure"]) > 0

    assert client.get(f"/api/recon/runs/{run['id']}").json()["id"] == run["id"]
    assert [r["id"] for r in client.get("/api/recon/runs").json()] == [run["id"]]

    breaks = client.get(f"/api/recon/runs/{run['id']}/breaks").json()
    assert len(breaks) == 10
    exposures = [Decimal(b["exposure"]) for b in breaks]
    assert exposures == sorted(exposures, reverse=True)
    assert all(b["status"] == "OPEN" for b in breaks)


def test_break_filters(client, fake_client):
    load_sample_day(fake_client)
    run_id = client.post("/api/recon/runs", json={"trade_date": "2026-10-14"}).json()["id"]
    price = client.get(f"/api/recon/runs/{run_id}/breaks", params={"break_type": "PRICE_MISMATCH"}).json()
    assert {b["trade_ref"] for b in price} == {"TRD-20261014-0007", "TRD-20261014-0019"}
    assert client.get(f"/api/recon/runs/{run_id}/breaks", params={"status": "RESOLVED"}).json() == []
    assert client.get(f"/api/recon/runs/{run_id}/breaks", params={"break_type": "NOPE"}).status_code == 422


def test_resolve_and_reopen_break(client, fake_client):
    fake_client.set_trades(DAY, [trade("A")], [trade("A", quantity=Decimal("90"))])
    run_id = client.post("/api/recon/runs", json={"trade_date": "2026-10-14"}).json()["id"]
    break_id = client.get(f"/api/recon/runs/{run_id}/breaks").json()[0]["id"]

    missing_comment = client.patch(f"/api/recon/breaks/{break_id}", json={"status": "RESOLVED", "comment": "  "})
    assert missing_comment.status_code == 422

    resolved = client.patch(
        f"/api/recon/breaks/{break_id}",
        json={"status": "RESOLVED", "comment": "Custodian confirmed partial fill", "resolved_by": "akshat"},
    ).json()
    assert resolved["status"] == "RESOLVED"
    assert resolved["resolved_by"] == "akshat"
    assert resolved["resolved_at"] is not None

    reopened = client.patch(f"/api/recon/breaks/{break_id}", json={"status": "OPEN"}).json()
    assert reopened["status"] == "OPEN"
    assert reopened["resolution_comment"] is None
    assert reopened["resolved_at"] is None


def test_summary_uses_latest_run_per_date(client, fake_client):
    empty = client.get("/api/recon/summary").json()
    assert empty["total_runs"] == 0
    assert empty["latest_run"] is None
    assert empty["open_breaks_by_type"] == []

    load_sample_day(fake_client)
    load_sample_day(fake_client, date(2026, 10, 13))
    first = client.post("/api/recon/runs", json={"trade_date": "2026-10-14"}).json()
    client.post("/api/recon/runs", json={"trade_date": "2026-10-14"})
    client.post("/api/recon/runs", json={"trade_date": "2026-10-13"})

    breaks = client.get(f"/api/recon/runs/{first['id']}/breaks").json()
    client.patch(f"/api/recon/breaks/{breaks[0]['id']}", json={"status": "RESOLVED", "comment": "old run"})

    summary = client.get("/api/recon/summary").json()
    assert summary["total_runs"] == 3
    assert summary["dates_reconciled"] == 2
    assert summary["open_breaks"] == 20
    assert summary["resolved_breaks"] == 0
    assert sum(t["count"] for t in summary["open_breaks_by_type"]) == 20
    assert Decimal(summary["open_exposure"]) == sum(Decimal(t["exposure"]) for t in summary["open_breaks_by_type"])
    assert summary["latest_run"]["trade_date"] == "2026-10-13"


def test_export_breaks_csv(client, fake_client):
    load_sample_day(fake_client)
    run_id = client.post("/api/recon/runs", json={"trade_date": "2026-10-14"}).json()["id"]
    response = client.get(f"/api/recon/runs/{run_id}/breaks.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert f"breaks_run{run_id}_2026-10-14.csv" in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("trade_ref,break_type")
    assert len(lines) == 11


def test_errors(client, fake_client):
    assert client.post("/api/recon/runs", json={"trade_date": "2026-01-01"}).status_code == 404
    assert client.post("/api/recon/runs", json={"trade_date": "bad"}).status_code == 422
    assert client.get("/api/recon/runs/999").status_code == 404
    assert client.get("/api/recon/runs/999/breaks").status_code == 404
    assert client.patch("/api/recon/breaks/999", json={"status": "OPEN"}).status_code == 404

    fake_client.fail = True
    failed = client.post("/api/recon/runs", json={"trade_date": "2026-10-14"})
    assert failed.status_code == 502
    assert "trade-service" in failed.json()["detail"]
