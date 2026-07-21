import pytest

from src.modules.integrations.meta.infrastructure.mock_client import MockMetaClient

META_TOKEN = "dev-meta-token"
AD_ACCOUNT = "act_1234567890"
META_CAMPAIGN_ID = "23851234567890"
START, END = "2026-07-01", "2026-07-03"
FALLBACK_INVESTMENT = 9999.0     # fora da faixa do mock (3 dias => R$150..R$750)


async def _admin(client):  # type: ignore[no-untyped-def]
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _funnel_investment(client, headers, store_id):  # type: ignore[no-untyped-def]
    res = await client.get(
        f"/marketing/funnel?store_id={store_id}&start={START}&end={END}", headers=headers)
    assert res.status_code == 200
    return res.json()["investment"]


@pytest.mark.asyncio
async def test_sync_requires_meta_token(client) -> None:  # type: ignore[no-untyped-def]
    missing = await client.post("/integrations/meta/sync", json={})
    assert missing.status_code == 401

    wrong = await client.post("/integrations/meta/sync", json={},
                              headers={"x-meta-token": "nope"})
    assert wrong.status_code == 401


@pytest.mark.asyncio
async def test_sync_writes_spend_and_funnel_uses_it(client) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin(client)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Meta"},
                               headers=headers)).json()
    store_id = store["id"]

    # ad account da loja (PATCH /admin/stores -> allowlist _UPDATABLE)
    patched = await client.patch(f"/admin/stores/{store_id}",
                                 json={"meta_ad_account_id": AD_ACCOUNT}, headers=headers)
    assert patched.status_code == 200

    # campanha + meta_campaign_id (PATCH /campaigns)
    campaign = (await client.post("/campaigns", json={
        "store_id": store_id, "name": "Meta Julho", "started_at": START,
    }, headers=headers)).json()
    updated = await client.patch(f"/campaigns/{campaign['id']}",
                                 json={"meta_campaign_id": META_CAMPAIGN_ID}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["meta_campaign_id"] == META_CAMPAIGN_ID

    # fallback antes do sync: lançamento manual em daily_indicators
    await client.post("/indicators", json={
        "store_id": store_id, "reference_date": "2026-07-02", "origin": "receptivo",
        "marketing_investment": FALLBACK_INVESTMENT,
    }, headers=headers)
    assert await _funnel_investment(client, headers, store_id) == FALLBACK_INVESTMENT

    # sync (mock, META_ENABLED=false) grava 3 dias x 1 campanha
    synced = await client.post("/integrations/meta/sync", json={
        "store_id": store_id, "since": START, "until": END,
    }, headers={"x-meta-token": META_TOKEN})
    assert synced.status_code == 200
    body = synced.json()
    assert body["rows_written"] == 3
    assert body["skipped_no_ad_account"] == 0

    # gasto esperado = mesmo mock determinístico usado pelo sync
    insights = await MockMetaClient().fetch_daily_insights(AD_ACCOUNT, [META_CAMPAIGN_ID], START, END)
    expected = round(sum(i.spend for i in insights), 2)
    assert expected > 0

    # o funil agora reflete SUM(campaign_daily_spend), não mais o lançamento manual
    after = await _funnel_investment(client, headers, store_id)
    assert after == pytest.approx(expected, abs=0.01)
    assert after != FALLBACK_INVESTMENT

    # idempotência: re-sync não duplica (upsert por campaign_id + reference_date)
    resynced = await client.post("/integrations/meta/sync", json={
        "store_id": store_id, "since": START, "until": END,
    }, headers={"x-meta-token": META_TOKEN})
    assert resynced.json()["rows_written"] == 3
    assert await _funnel_investment(client, headers, store_id) == pytest.approx(expected, abs=0.01)
