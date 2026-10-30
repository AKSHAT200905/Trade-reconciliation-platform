HEADER = "trade_ref,trade_date,settlement_date,instrument,side,quantity,price,currency,counterparty\n"


def upload(client, source, body, filename="trades.csv"):
    return client.post(
        "/api/trades/upload",
        data={"source": source},
        files={"file": (filename, (HEADER + body).encode(), "text/csv")},
    )


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_inserts_then_updates_same_refs(client):
    first = upload(client, "INTERNAL", "T-1,2026-10-14,2026-10-15,X1,BUY,100,10,USD,Citi\n")
    assert first.status_code == 200
    assert first.json() == {"source": "INTERNAL", "inserted": 1, "updated": 0, "rejected": []}

    second = upload(client, "INTERNAL", "T-1,2026-10-14,2026-10-15,X1,BUY,200,10,USD,Citi\n")
    assert second.json()["inserted"] == 0
    assert second.json()["updated"] == 1

    page = client.get("/api/trades", params={"source": "INTERNAL"}).json()
    assert page["total"] == 1
    assert page["items"][0]["quantity"] == "200.0000"


def test_same_ref_is_kept_separately_per_source(client):
    upload(client, "INTERNAL", "T-1,2026-10-14,2026-10-15,X1,BUY,100,10,USD,Citi\n")
    upload(client, "CUSTODIAN", "T-1,2026-10-14,2026-10-15,X1,BUY,100,10,USD,Citi\n")
    assert client.get("/api/trades").json()["total"] == 2


def test_upload_reports_rejected_rows(client):
    response = upload(
        client,
        "CUSTODIAN",
        "T-1,2026-10-14,2026-10-15,X1,BUY,100,10,USD,Citi\nT-2,2026-10-14,2026-10-15,X1,BUY,0,10,USD,Citi\n",
    )
    body = response.json()
    assert body["inserted"] == 1
    assert body["rejected"][0]["trade_ref"] == "T-2"


def test_upload_rejects_wrong_file_type_and_bad_csv(client):
    assert upload(client, "INTERNAL", "", filename="trades.xlsx").status_code == 400
    bad = client.post(
        "/api/trades/upload",
        data={"source": "INTERNAL"},
        files={"file": ("t.csv", b"a,b,c\n1,2,3\n", "text/csv")},
    )
    assert bad.status_code == 400
    assert "Missing required columns" in bad.json()["detail"]


def test_upload_rejects_unknown_source(client):
    assert upload(client, "BROKER", "T-1,2026-10-14,2026-10-15,X1,BUY,100,10,USD,Citi\n").status_code == 422


def test_create_single_trade(client):
    payload = {
        "trade_ref": "T-9",
        "trade_date": "2026-10-14",
        "settlement_date": "2026-10-15",
        "instrument": "us0378331005",
        "side": "sell",
        "quantity": "50",
        "price": "228.4",
        "currency": "usd",
        "counterparty": "Barclays",
    }
    response = client.post("/api/trades", params={"source": "CUSTODIAN"}, json=payload)
    assert response.status_code == 201
    assert response.json()["instrument"] == "US0378331005"
    assert response.json()["source"] == "CUSTODIAN"


def test_sample_data_and_date_summary(client):
    results = client.post("/api/trades/sample").json()
    assert {r["source"]: r["inserted"] for r in results} == {"INTERNAL": 80, "CUSTODIAN": 78}
    assert all(r["rejected"] == [] for r in results)

    dates = client.get("/api/trades/dates").json()
    assert dates == [
        {"trade_date": "2026-10-14", "internal_count": 40, "custodian_count": 39},
        {"trade_date": "2026-10-13", "internal_count": 40, "custodian_count": 39},
    ]

    for_date = client.get("/api/trades/by-date/2026-10-14").json()
    assert len(for_date) == 79


def test_filters_search_and_pagination(client):
    client.post("/api/trades/sample")
    page = client.get("/api/trades", params={"search": "9001", "limit": 10}).json()
    assert page["total"] == 2
    assert all("9001" in t["trade_ref"] for t in page["items"])

    paged = client.get("/api/trades", params={"trade_date": "2026-10-13", "limit": 5, "offset": 5}).json()
    assert paged["total"] == 79
    assert len(paged["items"]) == 5


def test_delete_by_date_and_all(client):
    client.post("/api/trades/sample")
    assert client.delete("/api/trades", params={"trade_date": "2026-10-13"}).json() == {"deleted": 79}
    assert client.get("/api/trades").json()["total"] == 79
    assert client.delete("/api/trades").json() == {"deleted": 79}
    assert client.get("/api/trades").json()["total"] == 0
