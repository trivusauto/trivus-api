"""Popula o banco com um cenário realista de uso (demo / desenvolvimento).

Monta o ecossistema da holding (serviços, planos, empresas, assinaturas em vários
status) e o operacional de várias lojas (equipe, funil CRM de 7 etapas, leads
distribuídos nos últimos meses com datas coerentes, histórico de etapas, campanhas,
indicadores diários, metas e planos de ação).

Idempotente: limpa os dados de domínio (preservando o admin) e recria tudo.

Uso:  uv run python -m scripts.seed_demo
Somente para o banco LOCAL/DEMO — nunca aponte para produção.
"""
import asyncio
import json
import random
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import text

from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.shared.infrastructure.database import SessionFactory

random.seed(42)
HASHER = Argon2PasswordHasher()
TODAY = date.today()
DEMO_PASSWORD = "demo123"

STAGES = [
    "RECEBIDOS", "CLASSIFICADOS", "QUALIFICADOS", "AGENDADOS",
    "EM ATENDIMENTO", "RESGATE", "VEICULOS COMPRADOS", "VEICULOS VENDIDOS",
]
NAMES = [
    "João Silva", "Maria Oliveira", "Pedro Santos", "Ana Costa", "Lucas Pereira",
    "Juliana Almeida", "Rafael Souza", "Fernanda Lima", "Bruno Rodrigues", "Camila Ferreira",
    "Gustavo Carvalho", "Patrícia Gomes", "Rodrigo Martins", "Aline Ribeiro", "Thiago Barbosa",
    "Larissa Rocha", "Felipe Araújo", "Beatriz Cardoso", "Marcelo Dias", "Natália Mendes",
    "Vinícius Nunes", "Carolina Moreira", "Diego Cavalcanti", "Isabela Freitas", "André Teixeira",
    "Priscila Correia", "Leonardo Pinto", "Amanda Ramos", "Eduardo Monteiro", "Vanessa Castro",
    "Gabriel Azevedo", "Renata Campos", "Fábio Nascimento", "Tatiane Moura", "Henrique Melo",
    "Sabrina Duarte", "Ricardo Fonseca", "Débora Vieira", "Alexandre Barros", "Luana Machado",
]
CITIES = [
    ("São Paulo", "SP"), ("Campinas", "SP"), ("Guarulhos", "SP"), ("Santo André", "SP"),
    ("Rio de Janeiro", "RJ"), ("Niterói", "RJ"), ("Belo Horizonte", "MG"), ("Contagem", "MG"),
    ("Curitiba", "PR"), ("Londrina", "PR"), ("Porto Alegre", "RS"), ("Caxias do Sul", "RS"),
]
MODELS = [
    "Onix", "HB20", "Corolla", "Civic", "Compass", "Renegade", "T-Cross", "Nivus", "Polo",
    "Kwid", "Strada", "Hilux", "Ranger", "Argo", "Creta", "Kicks", "Tracker", "Pulse", "Fastback",
]
COLORS = ["Branco", "Prata", "Preto", "Cinza", "Vermelho", "Azul"]
FUELS = ["Flex", "Diesel", "Gasolina", "Híbrido"]
URGENCIES = ["baixa", "media", "alta"]
CAMPAIGN_DEFS = [
    ("Google Ads — Seminovos", "gads-semi", 4500.0),
    ("Meta Ads — Ofertas da Semana", "meta-ofertas", 3200.0),
    ("Instagram — Lançamentos", "ig-lancamentos", 1800.0),
    ("Black Friday Veículos", "blackfriday", 6000.0),
]

# distribuição de quão longe cada lead avançou no funil (índice de etapa 0..7; 5=RESGATE)
REACHED_WEIGHTS = [(0, 14), (1, 14), (2, 16), (3, 13), (4, 10), (5, 9), (6, 8), (7, 16)]
# viés para meses recentes (offset 0 = mês atual)
MONTH_WEIGHTS = [(0, 28), (1, 18), (2, 14), (3, 10), (4, 8), (5, 8), (6, 7), (7, 7)]

LEAD_COLS = [
    "id", "store_id", "stage_id", "sort_order", "assigned_to", "vendedor_id", "agendado_por",
    "funil", "qualificado", "origem_mkt", "urgencia_venda", "nome", "telefone", "bairro", "cidade",
    "modelo", "veiculo", "ano", "cor", "combustivel", "quilometragem", "valor_tabela_fipe",
    "tem_financiamento", "valor_pretendido", "valor_compra", "data_comprado", "data_agendamento", "hora_agendamento",
    "data_marcacao_agendamento", "compareceu_agendamento", "data_compareceu", "fechou_negocio",
    "data_fechou_negocio", "receita", "despesa", "rentabilidade", "observacoes", "campaign_id",
    "created_at", "updated_at",
]


def wpick(weighted: list[tuple]) -> object:
    vals, weights = zip(*weighted)
    return random.choices(vals, weights=weights, k=1)[0]


def month_first(offset: int) -> date:
    y, m = TODAY.year, TODAY.month - offset
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def rand_created(offset: int) -> datetime:
    first = month_first(offset)
    if offset == 0:
        max_day = TODAY.day
    else:
        nxt = date(first.year + (first.month // 12), (first.month % 12) + 1, 1)
        max_day = (nxt - timedelta(days=1)).day
    d = first.replace(day=random.randint(1, max_day))
    return datetime(d.year, d.month, d.day, random.randint(8, 19), random.choice([0, 15, 30, 45]))


def clamp_past(d: date) -> date:
    return min(d, TODAY)


def phone() -> str:
    return f"({random.randint(11, 51)}) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"


async def insert(s, table: str, row: dict) -> None:
    cols = ", ".join(row.keys())
    ph = ", ".join(f":{k}" for k in row)
    await s.execute(text(f"INSERT INTO {table} ({cols}) VALUES ({ph})"), row)


async def clear_demo(s) -> None:
    for stmt in [
        "DELETE FROM service_interests",
        "DELETE FROM stores",              # cascata: usuários da loja, funis, leads, indicadores, metas, planos, campanhas, store_services
        "DELETE FROM crm_funnels",         # remove também os templates (store_id NULL)
        "DELETE FROM companies",           # cascata: assinaturas, pagamentos
        "DELETE FROM plans",
        "DELETE FROM services",
        "DELETE FROM bulk_send_contacts",
        "DELETE FROM bulk_sends",
        "DELETE FROM users WHERE role <> 'admin'",
    ]:
        await s.execute(text(stmt))


async def seed_ecosystem(s) -> dict:
    services = [
        ("crm", "CRM & Funil de Vendas", "software",
         "Kanban completo com etapas, agenda e captação de leads via WhatsApp.",
         "Organize leads do recebimento à venda com regras por etapa e histórico.",
         "Pare de perder lead no caderninho — cada oportunidade numa esteira clara.",
         ["crm.kanban", "crm.activity_log", "agenda", "webhook.zapi"]),
        ("metrics", "Métricas & BI", "software",
         "Dashboard, relatórios, projeções, metas e ranking de equipe.",
         "Enxergue conversão por etapa, receita e evolução mês a mês.",
         "Decisão por dado, não por achismo. Saiba onde o funil vaza.",
         ["metrics.dashboard", "metrics.reports", "metrics.projections", "metrics.team", "goals", "indicators", "action_plans"]),
        ("marketing", "Marketing & Performance", "software",
         "Campanhas, funil de custos (CPL/CAC) e comparativo por campanha.",
         "Ligue investimento de mídia ao resultado real de vendas.",
         "Descubra qual campanha traz venda e qual só queima verba.",
         ["marketing.campaigns", "metrics.marketing", "metrics.reports.costs"]),
        ("disparos", "Disparos em Massa", "software",
         "Envio em massa no WhatsApp com variações de mensagem e cadência.",
         "Reative base fria e aqueça leads com automação de disparo.",
         "Sua base parada virando agendamento com poucos cliques.",
         ["bulk_send"]),
        ("consultoria", "Consultoria de Gestão", "humano",
         "Acompanhamento estratégico mensal com especialista Trivus.",
         "Rotina de gestão, metas e ritual de performance com o dono.",
         "Um sócio de resultado ao seu lado todo mês.",
         []),
        ("capacitacao", "Capacitação de Equipe", "humano",
         "Treinamento de SDR e vendedores em técnicas de conversão.",
         "Time treinado converte mais do mesmo volume de leads.",
         "Mesma verba, mais venda: destrave a performance do time.",
         []),
        ("agencia", "Agência de Tráfego", "humano",
         "Gestão de tráfego pago e criativos feita pela agência Trivus.",
         "Campanhas gerenciadas de ponta a ponta pelo nosso time.",
         "Deixe a mídia com quem vive disso e foque em vender.",
         []),
    ]
    for i, (key, name, typ, wii, wid, pitch, fkeys) in enumerate(services):
        await insert(s, "services", {
            "id": str(uuid.uuid4()), "key": key, "name": name, "type": typ,
            "what_it_is": wii, "what_it_does": wid, "upsell_pitch": pitch,
            "feature_keys": json.dumps(fkeys), "sort_order": i, "active": True,
        })

    plans = [
        ("essencial", "Essencial", ["crm"], 3, 299.0),
        ("performance", "Performance", ["crm", "metrics", "marketing"], 10, 799.0),
        ("full", "Full", ["crm", "metrics", "marketing", "disparos"], 50, 1499.0),
    ]
    plan_ids = {}
    for key, name, skeys, maxst, price in plans:
        pid = str(uuid.uuid4())
        plan_ids[key] = pid
        await insert(s, "plans", {
            "id": pid, "key": key, "name": name, "service_keys": json.dumps(skeys),
            "max_stores": maxst, "price_month": price, "active": True,
        })
    return plan_ids


async def seed_company(s, name, cnpj, resp, plan_id, plan_services, status, trial_days=None):
    cid = str(uuid.uuid4())
    await insert(s, "companies", {
        "id": cid, "name": name, "cnpj": cnpj, "responsible_name": resp, "active": True,
    })
    trial_ends = (TODAY + timedelta(days=trial_days)) if trial_days is not None else None
    started = TODAY - timedelta(days=random.randint(60, 400)) if status in ("active", "suspended") else None
    await insert(s, "subscriptions", {
        "id": str(uuid.uuid4()), "company_id": cid, "plan_id": plan_id, "status": status,
        "trial_ends_at": trial_ends, "billing_mode": "manual", "started_at": started,
        "notes": None,
    })
    return cid, plan_services


async def seed_store(s, company_id, nome_fantasia, enabled_services, *, crm=True):
    sid = str(uuid.uuid4())
    await insert(s, "stores", {
        "id": sid, "nome_fantasia": nome_fantasia, "razao_social": f"{nome_fantasia} LTDA",
        "cnpj": f"{random.randint(10, 99)}.{random.randint(100, 999)}.{random.randint(100, 999)}/0001-{random.randint(10, 99)}",
        "nome_responsavel": random.choice(NAMES), "cidade": random.choice(CITIES)[0],
        "estado": "SP", "crm_enabled": crm, "zapi_webhook_enabled": True,
        "require_campaign_on_lead": False, "company_id": company_id, "active": True,
    })
    for svc in enabled_services:
        await insert(s, "store_services", {
            "id": str(uuid.uuid4()), "store_id": sid, "service_key": svc, "enabled": True,
        })
    return sid


async def seed_funnel(s, store_id, template_id, template_stage_ids):
    """Cria o funil da loja clonado do template (7 etapas). Retorna ids das etapas em ordem."""
    fid = str(uuid.uuid4())
    await insert(s, "crm_funnels", {
        "id": fid, "store_id": store_id, "name": "Funil Padrão", "sort_order": 0,
        "is_template": False, "template_source_id": template_id,
    })
    stage_ids = []
    for i, nm in enumerate(STAGES):
        stid = str(uuid.uuid4())
        stage_ids.append(stid)
        await insert(s, "crm_funnel_stages", {
            "id": stid, "funnel_id": fid, "name": nm, "sort_order": i,
            "template_stage_id": template_stage_ids[i],
        })
    return stage_ids


async def seed_template(s):
    fid = str(uuid.uuid4())
    await insert(s, "crm_funnels", {
        "id": fid, "store_id": None, "name": "Template Padrão Trivus", "sort_order": 0,
        "is_template": True, "template_source_id": None,
    })
    stage_ids = []
    for i, nm in enumerate(STAGES):
        stid = str(uuid.uuid4())
        stage_ids.append(stid)
        await insert(s, "crm_funnel_stages", {
            "id": stid, "funnel_id": fid, "name": nm, "sort_order": i, "template_stage_id": None,
        })
    return fid, stage_ids


async def seed_team(s, store_id):
    team = {"sdr": [], "vendedor": [], "gerente": None}
    people = [
        ("gerente", "Gerente"), ("sdr", "SDR 1"), ("sdr", "SDR 2"),
        ("vendedor", "Vendedor 1"), ("vendedor", "Vendedor 2"), ("administrativo", "Financeiro"),
    ]
    slug = store_id[:8]
    for role, label in people:
        uid = str(uuid.uuid4())
        await insert(s, "users", {
            "id": uid, "email": f"{role}.{label.split()[-1].lower()}.{slug}@trivus.local",
            "password_hash": HASHER.hash(DEMO_PASSWORD), "name": f"{label} — {store_id[:4]}",
            "role": "shop_user", "parent_store_id": store_id, "shop_role": role,
            "can_see_unassigned_leads": role in ("gerente", "administrativo"), "active": True,
        })
        if role == "gerente":
            team["gerente"] = uid
        elif role in ("sdr", "vendedor"):
            team[role].append(uid)
    return team


async def seed_campaigns(s, store_id):
    ids = []
    for name, code, budget in CAMPAIGN_DEFS:
        cid = str(uuid.uuid4())
        ids.append(cid)
        await insert(s, "marketing_campaigns", {
            "id": cid, "store_id": store_id, "name": name, "link_code": code,
            "started_at": TODAY - timedelta(days=random.randint(30, 120)),
            "ended_at": None, "budget": budget,
        })
    return ids


def build_lead(store_id, stage_ids, team, campaigns, offset):
    reached = wpick(REACHED_WEIGHTS)
    created = rand_created(offset)
    cdate = created.date()
    funil = wpick([("receptivo", 72), ("prospeccao_ativa", 22), ("outros", 6)])
    city, _uf = random.choice(CITIES)
    sdr = random.choice(team["sdr"]) if team["sdr"] else None
    vendedor = random.choice(team["vendedor"]) if team["vendedor"] else None
    row = {c: None for c in LEAD_COLS}
    row.update({
        "id": str(uuid.uuid4()), "store_id": store_id, "stage_id": stage_ids[reached],
        "sort_order": random.randint(0, 100), "assigned_to": sdr, "agendado_por": sdr,
        "funil": funil, "origem_mkt": None, "urgencia_venda": random.choice(URGENCIES),
        "nome": random.choice(NAMES), "telefone": phone(), "cidade": city,
        "bairro": random.choice(["Centro", "Jardins", "Vila Nova", "Boa Vista", "Industrial"]),
        "created_at": created, "updated_at": created,
        "campaign_id": (random.choice(campaigns) if (funil == "receptivo" and campaigns) else None),
    })
    if reached >= 1:  # CLASSIFICADOS
        row["observacoes"] = "Interesse em troca com entrada."
    if reached >= 2:  # QUALIFICADOS
        row.update({
            "qualificado": True, "modelo": random.choice(MODELS),
            "ano": str(random.randint(2016, 2024)), "cor": random.choice(COLORS),
            "combustivel": random.choice(FUELS), "quilometragem": str(random.randint(10, 120) * 1000),
            "valor_tabela_fipe": round(random.uniform(45000, 180000), 2),
            "tem_financiamento": random.choice([True, False]),
            "valor_pretendido": round(random.uniform(40000, 170000), 2),
        })
        row["veiculo"] = f"{row['modelo']} {row['ano']}"
    if reached >= 3:  # AGENDADOS
        marca = clamp_past(cdate + timedelta(days=random.randint(0, 3)))
        if reached == 3 and random.random() < 0.5:
            agend = TODAY + timedelta(days=random.randint(0, 14))  # agendamento futuro
        else:
            agend = clamp_past(cdate + timedelta(days=random.randint(1, 8)))
        row.update({
            "data_marcacao_agendamento": marca, "data_agendamento": agend,
            "hora_agendamento": f"{random.randint(9, 18):02d}:{random.choice(['00', '30'])}",
        })
    if reached >= 4:  # EM ATENDIMENTO (compareceu)
        comp = clamp_past(row["data_agendamento"] + timedelta(days=random.randint(0, 2)))
        row.update({"compareceu_agendamento": True, "data_compareceu": comp, "vendedor_id": vendedor})
    if reached == 5:  # RESGATE (atendido, não fechou — retomar contato)
        row["observacoes"] = "Não aceitou a proposta inicial. Retomar contato em 15 dias."
    if reached >= 6:  # VEICULOS COMPRADOS
        row["valor_compra"] = round(random.uniform(40000, 160000), 2)
        row["data_comprado"] = clamp_past(row["data_compareceu"] + timedelta(days=random.randint(0, 5)))
    if reached >= 7:  # VEICULOS VENDIDOS (fechou)
        receita = round(random.uniform(55000, 190000), 2)
        despesa = round(receita * random.uniform(0.82, 0.93), 2)
        fech = clamp_past(row["data_comprado"] + timedelta(days=random.randint(0, 7)))
        row.update({
            "fechou_negocio": True, "data_fechou_negocio": fech, "receita": receita,
            "despesa": despesa, "rentabilidade": round(receita - despesa, 2),
        })
    # histórico de etapas (entrou em cada etapa até a atual)
    history = []
    t = created
    for i in range(reached + 1):
        history.append({"id": str(uuid.uuid4()), "lead_id": row["id"],
                        "stage_id": stage_ids[i], "entered_at": t})
        t = t + timedelta(hours=random.randint(2, 40))
    return row, history


async def seed_leads(s, store_id, stage_ids, team, campaigns, n_leads):
    leads, history = [], []
    for _ in range(n_leads):
        row, hist = build_lead(store_id, stage_ids, team, campaigns, wpick(MONTH_WEIGHTS))
        leads.append(row)
        history.extend(hist)
    cols = ", ".join(LEAD_COLS)
    ph = ", ".join(f":{c}" for c in LEAD_COLS)
    await s.execute(text(f"INSERT INTO crm_funnel_leads ({cols}) VALUES ({ph})"), leads)
    if history:
        await s.execute(text(
            "INSERT INTO crm_lead_stage_history (id, lead_id, stage_id, entered_at) "
            "VALUES (:id, :lead_id, :stage_id, :entered_at)"), history)


async def seed_indicators(s, store_id, days_back=75):
    rows = []
    for d in range(days_back):
        ref = TODAY - timedelta(days=d)
        for origin, invest in (("receptivo", True), ("prospeccao", False)):
            total = random.randint(3, 14) if origin == "receptivo" else random.randint(1, 6)
            classified = int(total * random.uniform(0.6, 0.85))
            qualified = int(classified * random.uniform(0.6, 0.85))
            scheduled = int(qualified * random.uniform(0.5, 0.8))
            attended = int(scheduled * random.uniform(0.5, 0.85))
            converted = int(attended * random.uniform(0.4, 0.7))
            rows.append({
                "id": str(uuid.uuid4()), "store_id": store_id, "reference_date": ref, "origin": origin,
                "total_leads": total, "classified_leads": classified, "qualified_leads": qualified,
                "scheduled_leads": scheduled, "attended_leads": attended, "converted_leads": converted,
                "profitability": round(converted * random.uniform(4000, 9000), 2),
                "daily_expenses": round(random.uniform(200, 900), 2),
                "marketing_investment": round(random.uniform(150, 700), 2) if invest else None,
                "notes": None,
            })
    await s.execute(text(
        "INSERT INTO daily_indicators (id, store_id, reference_date, origin, total_leads, classified_leads, "
        "qualified_leads, scheduled_leads, attended_leads, converted_leads, profitability, daily_expenses, "
        "marketing_investment, notes) VALUES (:id, :store_id, :reference_date, :origin, :total_leads, "
        ":classified_leads, :qualified_leads, :scheduled_leads, :attended_leads, :converted_leads, "
        ":profitability, :daily_expenses, :marketing_investment, :notes)"), rows)


async def seed_goals(s, store_id):
    for offset in range(3):
        first = month_first(offset)
        for origin in ("receptivo", "prospeccao", "outros"):
            base = {"receptivo": 90, "prospeccao": 40, "outros": 15}[origin]
            await insert(s, "goals", {
                "id": str(uuid.uuid4()), "store_id": store_id, "month": first.month, "year": first.year,
                "origin": origin, "leads_quantity": base,
                "qualified_quantity": int(base * 0.55), "scheduled_quantity": int(base * 0.35),
                "attended_quantity": int(base * 0.25), "conversions_quantity": int(base * 0.15),
                "profitability_goal": round(base * 900.0, 2), "average_ticket_goal": 7500.0,
                "marketing_investment_goal": round(base * 120.0, 2) if origin == "receptivo" else None,
            })


async def seed_action_plans(s, store_id):
    plans = [
        ("Treinar SDRs em qualificação por telefone", "Roteiro de perguntas para elevar a taxa de qualificação.", "em_andamento"),
        ("Reduzir tempo de resposta do lead", "Meta: responder todo lead receptivo em até 5 min.", "a_fazer"),
        ("Campanha de reativação de base fria", "Disparo para leads sem contato há 60+ dias.", "a_fazer"),
        ("Revisar precificação de entrada", "Alinhar avaliação de troca com a FIPE.", "concluido"),
        ("Ritual semanal de pipeline", "Reunião de funil toda segunda com o time.", "em_andamento"),
    ]
    for title, desc, status in plans:
        await insert(s, "action_plans", {
            "id": str(uuid.uuid4()), "store_id": store_id, "title": title,
            "description": desc, "status": status,
        })


async def seed_interests(s, companies_stores):
    combos = [
        ("marketing", "novo"), ("disparos", "novo"), ("metrics", "contatado"),
        ("consultoria", "contatado"), ("capacitacao", "convertido"), ("agencia", "descartado"),
    ]
    for svc, status in combos:
        cid, sid = random.choice(companies_stores)
        await insert(s, "service_interests", {
            "id": str(uuid.uuid4()), "company_id": cid, "store_id": sid, "service_key": svc,
            "requested_by": None, "status": status, "notes": None,
            "created_at": datetime.now() - timedelta(days=random.randint(1, 40)),
        })


async def main() -> None:
    async with SessionFactory() as s:
        await clear_demo(s)
        plan_ids = await seed_ecosystem(s)
        template_id, template_stage_ids = await seed_template(s)

        # empresas × assinaturas × lojas
        auto_c, auto_svc = await seed_company(
            s, "Rede AutoStar", "11.111.111/0001-11", "Carlos AutoStar",
            plan_ids["full"], ["crm", "metrics", "marketing", "disparos"], "active")
        veloz_c, veloz_svc = await seed_company(
            s, "Grupo VelozCar", "22.222.222/0001-22", "Marina VelozCar",
            plan_ids["performance"], ["crm", "metrics", "marketing"], "active")
        nova_c, nova_svc = await seed_company(
            s, "NovaMarca Veículos", "33.333.333/0001-33", "Rafael NovaMarca",
            plan_ids["essencial"], ["crm"], "trialing", trial_days=9)
        antiga_c, antiga_svc = await seed_company(
            s, "Zeta Motors", "44.444.444/0001-44", "Sérgio Zeta",
            plan_ids["performance"], ["crm", "metrics", "marketing"], "suspended")

        stores = []  # (store_id, enabled_services, n_leads, with_ops)
        matriz = await seed_store(s, auto_c, "AutoStar — Matriz", auto_svc)
        stores.append((matriz, auto_svc, 130, True))
        filial = await seed_store(s, auto_c, "AutoStar — Filial Zona Sul", auto_svc)
        stores.append((filial, auto_svc, 45, True))
        veloz = await seed_store(s, veloz_c, "VelozCar Seminovos", veloz_svc)
        stores.append((veloz, veloz_svc, 40, True))
        nova = await seed_store(s, nova_c, "NovaMarca Veículos", nova_svc)
        stores.append((nova, nova_svc, 22, False))
        antiga = await seed_store(s, antiga_c, "Zeta Motors", antiga_svc)
        stores.append((antiga, antiga_svc, 10, False))

        # portal owners (role client) — um por empresa, vinculados às lojas (user_store_access)
        owner_stores = {"carlos": [matriz, filial], "marina": [veloz], "rafael": [nova]}
        for cname, store_ids in owner_stores.items():
            uid = str(uuid.uuid4())
            await insert(s, "users", {
                "id": uid, "email": f"{cname}@trivus.local",
                "password_hash": HASHER.hash(DEMO_PASSWORD), "name": cname.capitalize(),
                "role": "client", "active": True,
            })
            for sid in store_ids:
                await insert(s, "user_store_access", {
                    "id": str(uuid.uuid4()), "user_id": uid, "store_id": sid, "is_owner": True,
                })

        companies_stores = [(auto_c, matriz), (veloz_c, veloz), (nova_c, nova)]
        await seed_interests(s, companies_stores)

        for store_id, _svc, n_leads, with_ops in stores:
            team = await seed_team(s, store_id)
            stage_ids = await seed_funnel(s, store_id, template_id, template_stage_ids)
            campaigns = await seed_campaigns(s, store_id) if with_ops else []
            await seed_leads(s, store_id, stage_ids, team, campaigns, n_leads)
            await seed_goals(s, store_id)
            await seed_action_plans(s, store_id)
            if with_ops:
                await seed_indicators(s, store_id)

        await s.commit()
    print("Seed demo concluído:")
    print("  4 empresas · 5 lojas · catálogo de 7 serviços · 3 planos")
    print("  ~247 leads no CRM, campanhas, indicadores diários, metas e planos de ação")
    print("  login admin: admin@trivus.local / admin123")
    print(f"  usuários demo (owners/equipe): senha '{DEMO_PASSWORD}'")


if __name__ == "__main__":
    asyncio.run(main())
