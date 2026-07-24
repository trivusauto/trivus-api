"""E2E dos patches de lead que escrevem DATAS (agendamento/comparecimento/fechamento).

Regressão do bug: LeadPatch produz datas como string ISO ("2026-07-20") e as
colunas são DATE — o asyncpg exige datetime.date, então o PATCH estourava 500.
"""
import pytest
from httpx import AsyncClient


async def _admin(client: AsyncClient) -> dict[str, str]:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _store_with_funnel(client: AsyncClient, headers: dict[str, str]) -> tuple[str, str]:
    """Cria template + loja com CRM ligado e devolve (store_id, primeira_stage_id)."""
    await client.post(
        "/admin/crm/templates",
        json={"name": "Tpl Patches", "stages": ["RECEBIDOS", "AGENDADOS"]},
        headers=headers,
    )
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Patches"}, headers=headers)).json()
    await client.patch(f"/admin/stores/{store['id']}", json={"crm_enabled": True}, headers=headers)
    funnels = (await client.get(f"/crm/funnels?store_id={store['id']}", headers=headers)).json()
    assert funnels, "loja com crm_enabled deveria ter funil clonado do template"
    return store["id"], funnels[0]["stages"][0]["id"]


@pytest.mark.asyncio
async def test_agendamento_comparecimento_fechamento_com_datas_iso(client: AsyncClient) -> None:
    headers = await _admin(client)
    store_id, stage_id = await _store_with_funnel(client, headers)
    lead = (await client.post(
        "/crm/leads",
        json={"store_id": store_id, "stage_id": stage_id, "funil": "receptivo", "nome": "Lead Datas", "telefone": "(11) 90000-0001"},
        headers=headers,
    )).json()

    # agendamento: strings ISO como o front/agente mandam → 200 e campos derivados
    res = await client.patch(
        f"/crm/leads/{lead['id']}/agendamento",
        json={"data_agendamento": "2026-07-20", "hora_agendamento": "14:30"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["data_agendamento"] == "2026-07-20"
    assert body["hora_agendamento"] == "14:30:00"
    assert body["agendado_por"] is not None
    assert body["data_marcacao_agendamento"] is not None

    # comparecimento: seta data_compareceu (string ISO internamente)
    res = await client.patch(f"/crm/leads/{lead['id']}/comparecimento", json={"compareceu": True}, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["compareceu_agendamento"] is True
    assert res.json()["data_compareceu"] is not None

    # fechamento: seta data_fechou_negocio + valores monetários em string
    res = await client.patch(
        f"/crm/leads/{lead['id']}/fechamento",
        json={"receita": "10000", "despesa": "8000", "rentabilidade": "2000"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["fechou_negocio"] is True
    assert res.json()["data_fechou_negocio"] is not None

    # cancelamento: nulls limpam agendamento e agendado_por
    res = await client.patch(
        f"/crm/leads/{lead['id']}/agendamento",
        json={"data_agendamento": None, "hora_agendamento": None},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["data_agendamento"] is None
    assert res.json()["agendado_por"] is None


FULL_STAGES = [
    "RECEBIDOS", "CLASSIFICADOS", "QUALIFICADOS", "AGENDADOS",
    "EM ATENDIMENTO", "RESGATE", "VEICULOS COMPRADOS", "VEICULOS VENDIDOS",
]


@pytest.mark.asyncio
async def test_resgate_e_carimbos_de_datas_por_coluna(client: AsyncClient) -> None:
    """RESGATE entre atendimento e compra; mover p/ COMPRADOS carimba data_comprado;
    valores monetários e datas retroativas editáveis via PATCH."""
    headers = await _admin(client)
    me = (await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})).json()["user"]

    # garante que exista template; o clone usa o primeiro do banco, então completamos
    # o funil clonado com as etapas que faltarem (independe da ordem dos templates)
    await client.post("/admin/crm/templates", json={"name": "Tpl Resgate", "stages": FULL_STAGES}, headers=headers)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Resgate"}, headers=headers)).json()
    await client.patch(f"/admin/stores/{store['id']}", json={"crm_enabled": True}, headers=headers)
    funnel = (await client.get(f"/crm/funnels?store_id={store['id']}", headers=headers)).json()[0]
    existing = {s["name"] for s in funnel["stages"]}
    next_order = max(s["sort_order"] for s in funnel["stages"]) + 1
    for name in FULL_STAGES:
        if name not in existing:
            await client.post("/crm/stages", json={"funnel_id": funnel["id"], "name": name, "sort_order": next_order}, headers=headers)
            next_order += 1
    funnel = (await client.get(f"/crm/funnels?store_id={store['id']}", headers=headers)).json()[0]
    by_name = {s["name"]: s["id"] for s in funnel["stages"]}

    lead = (await client.post(
        "/crm/leads",
        json={"store_id": store["id"], "stage_id": by_name["RECEBIDOS"], "funil": "receptivo",
              "nome": "Cliente Resgate", "telefone": "(11) 90000-0002", "cidade": "Campinas",
              "modelo": "Compass", "ano": "2022"},
        headers=headers,
    )).json()

    # completa exigências até EM ATENDIMENTO + valores (agora aceitos no PATCH)
    await client.patch(f"/crm/leads/{lead['id']}/agendamento",
                       json={"data_agendamento": "2026-07-10", "hora_agendamento": "10:00"}, headers=headers)
    await client.patch(f"/crm/leads/{lead['id']}/comparecimento", json={"compareceu": True}, headers=headers)
    res = await client.patch(
        f"/crm/leads/{lead['id']}",
        json={"vendedor_id": me["id"], "valor_pretendido": "70.000,00", "valor_compra": "85000"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["valor_pretendido"] == 70000.0
    assert res.json()["valor_compra"] == 85000.0

    # RESGATE: sem exigências próprias — cascata até EM ATENDIMENTO satisfeita
    res = await client.patch(f"/crm/leads/{lead['id']}/stage", json={"to_stage_id": by_name["RESGATE"]}, headers=headers)
    assert res.status_code == 200, res.text

    # mover p/ COMPRADOS carimba data_comprado = hoje (editável depois)
    res = await client.patch(f"/crm/leads/{lead['id']}/stage",
                             json={"to_stage_id": by_name["VEICULOS COMPRADOS"]}, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["data_comprado"] is not None

    res = await client.patch(f"/crm/leads/{lead['id']}", json={"data_comprado": "2026-06-10"}, headers=headers)
    assert res.json()["data_comprado"] == "2026-06-10"

    # fechamento + data de venda retroativa
    await client.patch(f"/crm/leads/{lead['id']}/fechamento",
                       json={"receita": "95000", "despesa": "86000", "rentabilidade": "9000"}, headers=headers)
    res = await client.patch(f"/crm/leads/{lead['id']}/stage",
                             json={"to_stage_id": by_name["VEICULOS VENDIDOS"]}, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["fechou_negocio"] is True

    res = await client.patch(f"/crm/leads/{lead['id']}", json={"data_fechou_negocio": "2026-06-15"}, headers=headers)
    assert res.json()["data_fechou_negocio"] == "2026-06-15"


@pytest.mark.asyncio
async def test_stage_entered_at_muda_ao_mover_de_etapa(client: AsyncClient) -> None:
    """O board expõe a data de entrada na etapa ATUAL (S2.4)."""
    headers = await _admin(client)
    store_id, first_stage = await _store_with_funnel(client, headers)
    funnels = (await client.get(f"/crm/funnels?store_id={store_id}", headers=headers)).json()
    stages = funnels[0]["stages"]
    target_stage = stages[1]["id"]

    lead = (await client.post(
        "/crm/leads",
        json={
            "store_id": store_id,
            "stage_id": first_stage,
            "funil": "receptivo",
            "nome": "Lead Entrada",
            "telefone": "(11) 90000-0009",
        },
        headers=headers,
    )).json()

    def _entered(board: list[dict[str, object]]) -> object:
        return next(item["stage_entered_at"] for item in board if item["id"] == lead["id"])

    # Lead nunca movido não tem histórico de etapa — o board devolve None (o front
    # faz fallback para a data de criação).
    board = (await client.get(f"/crm/leads?store_id={store_id}", headers=headers)).json()
    before = _entered(board)
    assert before is None

    await client.patch(
        f"/crm/leads/{lead['id']}/agendamento",
        json={"data_agendamento": "2026-07-20", "hora_agendamento": "14:30"},
        headers=headers,
    )
    res = await client.patch(f"/crm/leads/{lead['id']}/stage", json={"to_stage_id": target_stage}, headers=headers)
    assert res.status_code == 200, res.text

    board = (await client.get(f"/crm/leads?store_id={store_id}", headers=headers)).json()
    after = _entered(board)
    assert after is not None, "após mover, a etapa atual tem data de entrada"
    assert after != before
