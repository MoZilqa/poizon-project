async def test_site_is_admin_only(client):
    # покупатели работают через бота: без входа доступен только логин
    for path in ("/api/meta", "/api/calc", "/api/admin/meta", "/api/admin/settings"):
        assert (await client.get(path)).status_code in (401, 404, 405)
    assert (await client.post("/api/admin/calc", json={"category": "shoes", "price_cny": 500})).status_code == 401


async def test_calc_admin(admin):
    r = await admin.post("/api/admin/calc", json={"category": "shoes", "price_cny": 500})
    assert r.status_code == 200 and r.json()["total"] == "8687.50"
    assert (await admin.post("/api/admin/calc", json={"category": "shoes", "price_cny": 0})).status_code == 422


async def test_admin_requires_login(client):
    assert (await client.get("/api/admin/orders")).status_code == 401
    assert (await client.post("/api/auth/login", json={"password": "wrong"})).status_code == 401
    client.headers["Authorization"] = "Bearer 9999999999.forged"
    assert (await client.get("/api/admin/orders")).status_code == 401


async def test_orders_flow(admin, order):
    page = (await admin.get("/api/admin/orders", params={"status": "active"})).json()
    assert page["total"] == 1 and page["items"][0]["allowed"] == ["awaiting_payment", "cancelled"]
    assert (await admin.get("/api/admin/orders", params={"q": "@client"})).json()["total"] == 1
    assert (await admin.get("/api/admin/orders", params={"q": "nobody"})).json()["total"] == 0

    r = await admin.post(f"/api/admin/orders/{order.id}/status", json={"status": "paid"})
    assert r.status_code == 400
    r = await admin.post(f"/api/admin/orders/{order.id}/status", json={"status": "awaiting_payment"})
    assert r.status_code == 200 and [h["status"] for h in r.json()["history"]] == ["new", "awaiting_payment"]

    stats = (await admin.get("/api/admin/stats")).json()
    assert stats["active"] == 1 and stats["counts"]["awaiting_payment"] == 1


async def test_settings_validation(admin):
    manual = {"rate_auto": "0"}
    assert (await admin.put("/api/admin/settings", json={**manual, "rate": "abc"})).status_code == 400
    r = await admin.put("/api/admin/settings", json={**manual, "rate": "13", "requisites": "Сбер 2202..."})
    assert r.json()["rate"] == "13" and r.json()["requisites"] == "Сбер 2202..."
    calc = (await admin.post("/api/admin/calc", json={"category": "accessories", "price_cny": 100})).json()
    assert calc["goods"] == "1300.00"


async def test_auto_rate(admin, monkeypatch):
    from decimal import Decimal
    from app.core import rates

    async def fake():
        return Decimal("12.068")
    monkeypatch.setattr(rates, "fetch_cny", fake)

    cfg = (await admin.post("/api/admin/rate/sync")).json()
    assert cfg["rate_cbr"] == "12.0680" and cfg["rate"] == "12.0680" and cfg["rate_synced_at"]
    # надбавка пересчитывает курс из сохранённого значения ЦБ; ручной курс и служебные поля игнорируются
    cfg = (await admin.put("/api/admin/settings", json={"rate_extra": "5", "rate": "99", "rate_cbr": "1"})).json()
    assert cfg["rate"] == "12.6714" and cfg["rate_cbr"] == "12.0680"


async def test_auto_rate_failure_keeps_old(admin, monkeypatch):
    from app.core import rates

    async def broken():
        raise RuntimeError("ЦБ недоступен")
    monkeypatch.setattr(rates, "fetch_cny", broken)
    assert (await admin.post("/api/admin/rate/sync")).status_code == 502
    cfg = (await admin.get("/api/admin/settings")).json()
    assert cfg["rate"] == "12.5" and "ЦБ недоступен" in cfg["rate_error"]
