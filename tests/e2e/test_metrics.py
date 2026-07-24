import uuid
from datetime import date

import pytest
from httpx import AsyncClient


async def _admin_token(client: AsyncClient) -> str:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return str(res.json()["access_token"])


@pytest.mark.asyncio
async def test_dashboard_empty(client: AsyncClient) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/admin/stores", json={"nome_fantasia": "Metrics Store"}, headers=headers)
    store_id = created.json()["id"]
    res = await client.get(f"/metrics/dashboard?store_id={store_id}&start=2026-01-01&end=2026-12-31", headers=headers)
    assert res.status_code == 200
    assert res.json()["totals"]["total_leads"] == 0


@pytest.mark.asyncio
async def test_team_empty(client: AsyncClient) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/admin/stores", json={"nome_fantasia": "Metrics Store 2"}, headers=headers)
    store_id = created.json()["id"]
    res = await client.get(f"/metrics/team?store_id={store_id}&start=2026-01-01&end=2026-12-31", headers=headers)
    assert res.status_code == 200
    assert res.json()["rows"] == []


@pytest.mark.asyncio
async def test_dashboard_conta_classificados(client: AsyncClient) -> None:
    """O funil do dashboard inclui a etapa CLASSIFICADOS (S2.6)."""
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    wanted = ["RECEBIDOS", "CLASSIFICADOS", "QUALIFICADOS"]
    await client.post(
        "/admin/crm/templates", json={"name": "Tpl Classificados", "stages": wanted}, headers=headers
    )
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Classificados"}, headers=headers)).json()
    store_id = store["id"]
    await client.patch(f"/admin/stores/{store_id}", json={"crm_enabled": True}, headers=headers)

    # o clone usa o PRIMEIRO template do banco, então completamos o funil com o que faltar
    funnel = (await client.get(f"/crm/funnels?store_id={store_id}", headers=headers)).json()[0]
    existing = {s["name"] for s in funnel["stages"]}
    next_order = max(s["sort_order"] for s in funnel["stages"]) + 1
    for name in wanted:
        if name not in existing:
            await client.post(
                "/crm/stages",
                json={"funnel_id": funnel["id"], "name": name, "sort_order": next_order},
                headers=headers,
            )
            next_order += 1
    funnel = (await client.get(f"/crm/funnels?store_id={store_id}", headers=headers)).json()[0]
    stages = {s["name"]: s["id"] for s in funnel["stages"]}

    lead = (await client.post(
        "/crm/leads",
        json={
            "store_id": store_id,
            "stage_id": stages["RECEBIDOS"],
            "funil": "receptivo",
            "nome": "Lead Classificado",
            "telefone": "(11) 90000-0100",
            "cidade": "Belo Horizonte",
        },
        headers=headers,
    )).json()
    # o funil clonado pode ter etapas intermediárias com obrigatórios próprios;
    # preenchemos para que a movimentação até CLASSIFICADOS não seja barrada
    await client.patch(
        f"/crm/leads/{lead['id']}/agendamento",
        json={"data_agendamento": "2026-07-20", "hora_agendamento": "10:00"},
        headers=headers,
    )
    moved = await client.patch(
        f"/crm/leads/{lead['id']}/stage", json={"to_stage_id": stages["CLASSIFICADOS"]}, headers=headers
    )
    assert moved.status_code == 200, moved.text

    res = await client.get(
        f"/metrics/dashboard?store_id={store_id}&start=2026-01-01&end=2026-12-31", headers=headers
    )
    assert res.status_code == 200
    totals = res.json()["totals"]
    assert "classified_leads" in totals, "o funil precisa expor a etapa CLASSIFICADOS"
    assert totals["total_leads"] == 1
    assert totals["classified_leads"] == 1


async def _store_com_funil(client: AsyncClient, headers: dict[str, str], nome: str) -> tuple[str, str]:
    await client.post("/admin/crm/templates", json={"name": f"tpl-{nome}", "stages": ["RECEBIDOS"]}, headers=headers)
    store = (await client.post("/admin/stores", json={"nome_fantasia": nome}, headers=headers)).json()
    await client.patch(f"/admin/stores/{store['id']}", json={"crm_enabled": True}, headers=headers)
    funnel = (await client.get(f"/crm/funnels?store_id={store['id']}", headers=headers)).json()[0]
    return store["id"], funnel["stages"][0]["id"]


@pytest.mark.asyncio
async def test_dashboard_multi_loja_consolida_e_separa(client: AsyncClient) -> None:
    """store_ids devolve consolidated + by_store; consolidado é a soma (S4.2)."""
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    sid_a, stage_a = await _store_com_funil(client, headers, f"Multi A {uuid.uuid4().hex[:6]}")
    sid_b, stage_b = await _store_com_funil(client, headers, f"Multi B {uuid.uuid4().hex[:6]}")

    for i in range(2):
        await client.post("/crm/leads", json={
            "store_id": sid_a, "stage_id": stage_a, "funil": "receptivo",
            "nome": f"A{i}", "telefone": "(11) 90000-0000",
        }, headers=headers)
    await client.post("/crm/leads", json={
        "store_id": sid_b, "stage_id": stage_b, "funil": "receptivo",
        "nome": "B0", "telefone": "(11) 90000-0001",
    }, headers=headers)

    qs = f"store_ids={sid_a}&store_ids={sid_b}&start=2026-01-01&end=2026-12-31"
    res = await client.get(f"/metrics/dashboard?{qs}", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["consolidated"]["totals"]["total_leads"] == 3
    por_loja = {b["store_id"]: b for b in body["by_store"]}
    assert por_loja[sid_a]["totals"]["total_leads"] == 2
    assert por_loja[sid_b]["totals"]["total_leads"] == 1
    assert por_loja[sid_a]["store_name"].startswith("Multi A")

    # a soma das lojas bate com o consolidado
    soma = sum(b["totals"]["total_leads"] for b in body["by_store"])
    assert soma == body["consolidated"]["totals"]["total_leads"]


@pytest.mark.asyncio
async def test_dashboard_sem_store_ids_mantem_formato_antigo(client: AsyncClient) -> None:
    """Compat: sem store_ids a resposta continua {totals, monthly} (S4.2)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Compat"}, headers=headers)).json()
    res = await client.get(
        f"/metrics/dashboard?store_id={store['id']}&start=2026-01-01&end=2026-12-31", headers=headers
    )
    assert res.status_code == 200
    body = res.json()
    assert "totals" in body and "monthly" in body
    assert "consolidated" not in body


@pytest.mark.asyncio
async def test_dashboard_store_id_alheio_403(client: AsyncClient) -> None:
    """Loja fora do escopo derruba a requisição inteira (S4.2)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    minha = (await client.post("/admin/stores", json={"nome_fantasia": "Dono Minha"}, headers=headers)).json()
    alheia = (await client.post("/admin/stores", json={"nome_fantasia": "Dono Alheia"}, headers=headers)).json()

    email = f"dono_multi_{uuid.uuid4().hex[:8]}@example.com"
    dono = (await client.post(
        "/admin/users", json={"email": email, "password": "demo123", "name": "Dono Multi"}, headers=headers
    )).json()
    await client.put(f"/admin/users/{dono['id']}/stores",
                     json={"store_ids": [minha["id"]], "owner_store_ids": [minha["id"]]}, headers=headers)

    login = await client.post("/auth/login", json={"email": email, "password": "demo123"})
    dono_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    ok = await client.get(
        f"/metrics/dashboard?store_ids={minha['id']}&start=2026-01-01&end=2026-12-31", headers=dono_headers
    )
    assert ok.status_code == 200, ok.text

    negado = await client.get(
        f"/metrics/dashboard?store_ids={minha['id']}&store_ids={alheia['id']}"
        "&start=2026-01-01&end=2026-12-31",
        headers=dono_headers,
    )
    assert negado.status_code == 403


@pytest.mark.asyncio
async def test_marketing_series_dias_totais_e_comparativo(client: AsyncClient) -> None:
    """Série diária + totals + previous_totals da janela anterior (S4.4)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    store = (await client.post(
        "/admin/stores", json={"nome_fantasia": f"Serie {uuid.uuid4().hex[:6]}"}, headers=headers
    )).json()
    sid = store["id"]

    async def lancar(dia: str, leads: int, classificados: int, investimento: float) -> None:
        res = await client.post("/indicators", json={
            "store_id": sid, "reference_date": dia, "origin": "receptivo",
            "total_leads": leads, "classified_leads": classificados,
            "marketing_investment": investimento,
        }, headers=headers)
        assert res.status_code == 201, res.text

    # janela atual: 10 e 11 de julho · janela anterior (8 e 9): só o dia 9
    await lancar("2026-07-10", 10, 8, 500.0)
    await lancar("2026-07-11", 6, 4, 300.0)
    await lancar("2026-07-09", 4, 2, 200.0)

    res = await client.get(
        f"/metrics/marketing/series?store_id={sid}&from=2026-07-10&to=2026-07-11", headers=headers
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert [d["date"] for d in body["days"]] == ["2026-07-10", "2026-07-11"]
    assert body["days"][0]["leads"] == 10
    assert body["days"][0]["classificados"] == 8
    assert body["days"][0]["investimento"] == 500.0

    assert body["totals"]["leads"] == 16
    assert body["totals"]["investimento"] == 800.0

    # janela anterior de mesma duração (2 dias): 08 e 09/07 → só o dia 9 tem dado
    assert body["previous_range"] == {"from": "2026-07-08", "to": "2026-07-09"}
    assert body["previous_totals"]["leads"] == 4
    assert body["previous_totals"]["investimento"] == 200.0


@pytest.mark.asyncio
async def test_marketing_series_loja_alheia_403(client: AsyncClient) -> None:
    """O guard de loja vale para a série (S4.4)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    minha = (await client.post("/admin/stores", json={"nome_fantasia": "Serie Minha"}, headers=headers)).json()
    alheia = (await client.post("/admin/stores", json={"nome_fantasia": "Serie Alheia"}, headers=headers)).json()

    email = f"dono_serie_{uuid.uuid4().hex[:8]}@example.com"
    dono = (await client.post(
        "/admin/users", json={"email": email, "password": "demo123", "name": "Dono Serie"}, headers=headers
    )).json()
    await client.put(f"/admin/users/{dono['id']}/stores",
                     json={"store_ids": [minha["id"]], "owner_store_ids": [minha["id"]]}, headers=headers)
    login = await client.post("/auth/login", json={"email": email, "password": "demo123"})
    dono_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = await client.get(
        f"/metrics/marketing/series?store_id={alheia['id']}&from=2026-07-01&to=2026-07-31",
        headers=dono_headers,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_projecoes_sdr_forcado_ao_proprio_escopo(client: AsyncClient) -> None:
    """SDR comum recebe só os PRÓPRIOS números mesmo passando o id de outro (S4.9)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    sid, stage = await _store_com_funil(client, headers, f"Proj {uuid.uuid4().hex[:6]}")

    async def team(nome: str, role: str) -> tuple[str, dict[str, str]]:
        email = f"{role}_{uuid.uuid4().hex[:8]}@example.com"
        u = (await client.post(f"/stores/{sid}/team", json={
            "email": email, "password": "demo123", "name": nome, "shop_role": role,
        }, headers=headers)).json()
        login = await client.post("/auth/login", json={"email": email, "password": "demo123"})
        return u["id"], {"Authorization": f"Bearer {login.json()['access_token']}"}

    sdr_id, sdr_headers = await team("SDR Proj", "sdr")
    outro_id, _ = await team("Outro Proj", "vendedor")

    hoje = date.today()
    # 1 lead do SDR, 2 do colega
    for nome, dono in (("MEU", sdr_id), ("ALHEIO_1", outro_id), ("ALHEIO_2", outro_id)):
        await client.post("/crm/leads", json={
            "store_id": sid, "stage_id": stage, "funil": "receptivo",
            "nome": nome, "telefone": "(11) 90000-0000", "assigned_to": dono,
        }, headers=headers)

    def leads_de(body: dict[str, object]) -> float:
        metrics = body["metrics"]  # type: ignore[index]
        return float(next(m for m in metrics if m["key"] == "leads")["actual"])  # type: ignore[index]

    qs = f"year={hoje.year}&month={hoje.month}&store_id={sid}"

    # admin vê os 3
    todos = (await client.get(f"/metrics/projections?{qs}", headers=headers)).json()
    assert leads_de(todos) == 3

    # SDR vê só o próprio...
    meu = (await client.get(f"/metrics/projections?{qs}", headers=sdr_headers)).json()
    assert leads_de(meu) == 1

    # ...e continua vendo só o próprio ao tentar passar o id do colega
    tentativa = (await client.get(
        f"/metrics/projections?{qs}&user_id={outro_id}", headers=sdr_headers
    )).json()
    assert leads_de(tentativa) == 1, "o backend ignora o user_id enviado por shop_user comum"


@pytest.mark.asyncio
async def test_projecoes_por_origem_e_classificados(client: AsyncClient) -> None:
    """A resposta separa por origem e inclui a métrica classified (S4.9)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    sid, stage = await _store_com_funil(client, headers, f"ProjOrig {uuid.uuid4().hex[:6]}")

    for nome, funil in (("R1", "receptivo"), ("R2", "receptivo"), ("P1", "prospeccao_ativa")):
        await client.post("/crm/leads", json={
            "store_id": sid, "stage_id": stage, "funil": funil,
            "nome": nome, "telefone": "(11) 90000-0000",
        }, headers=headers)

    hoje = date.today()
    body = (await client.get(
        f"/metrics/projections?year={hoje.year}&month={hoje.month}&store_id={sid}", headers=headers
    )).json()

    assert any(m["key"] == "classified" for m in body["metrics"]), "classificados entra nas projeções"
    assert set(body["by_origin"]) == {"receptivo", "prospeccao", "outros"}

    def leads(bloco: list[dict[str, object]]) -> float:
        return float(next(m for m in bloco if m["key"] == "leads")["actual"])

    assert leads(body["by_origin"]["receptivo"]) == 2
    assert leads(body["by_origin"]["prospeccao"]) == 1
    assert leads(body["total"]) == 3
