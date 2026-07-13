# Plano 05 — CRM (código completo)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 01–04. Todo código é copia-e-cola; rode os testes em cada passo.

**Goal:** Kanban via API — funis, etapas, leads, regras de campo por coluna, validação de avanço, histórico, cooling, atividade, clone de funil-template em transação, e patches de agendamento/comparecimento/fechamento.

**Architecture:** Módulo `crm`. Regras de negócio = serviços de domínio puros. Leads trafegam como `dict` (espelha o payload do produto). Spec §6.4, §6.8, §6.9, §6.10, §8.1, §10.7.

**Tech Stack:** mesmo do Plano 03.

> Crie os `__init__.py` de `src/modules/crm/` e subpastas (`domain`, `application`, `infrastructure`, `interface`) e de `tests/unit/crm/` no início.

---

## Task 1: Serviço de domínio `StageRules`

**Files:** `src/modules/crm/domain/stage_rules.py` + `tests/unit/crm/test_stage_rules.py`

- [ ] **Step 1: Teste**

`tests/unit/crm/test_stage_rules.py`:
```python
from src.modules.crm.domain.stage_rules import StageRules

STAGES = [{"name": n} for n in ["RECEBIDOS","CLASSIFICADOS","QUALIFICADOS","AGENDADOS","EM ATENDIMENTO","VEÍCULOS COMPRADOS","VEÍCULOS VENDIDOS"]]
s = StageRules()


def test_normalize() -> None:
    assert s.normalize_stage_name("Veículos Vendidos") == "VEICULOS VENDIDOS"


def test_missing_to_advance() -> None:
    ok, missing = s.can_advance(STAGES, 0, 2, {"funil": "receptivo", "telefone": "11999999999"})
    assert ok is False
    assert sorted(m["field"] for m in missing) == ["ano", "cidade", "modelo", "nome"]


def test_allow_when_filled() -> None:
    assert s.can_advance(STAGES, 0, 1, {"funil": "r", "telefone": "1", "nome": "Ana", "cidade": "SP"})[0] is True


def test_em_atendimento_rules() -> None:
    base = {"funil": "r", "telefone": "1", "nome": "A", "cidade": "C", "modelo": "M", "ano": "2020", "data_agendamento": "2026-01-01", "hora_agendamento": "10:00"}
    assert s.can_advance(STAGES, 0, 4, {**base, "compareceu_agendamento": False})[0] is False
    assert s.can_advance(STAGES, 0, 4, {**base, "compareceu_agendamento": True, "vendedor_id": "v1"})[0] is True


def test_auto_stage_index() -> None:
    assert s.compute_auto_stage_index(STAGES, {"funil": "r", "telefone": "1", "nome": "A", "cidade": "C"}) == 1


def test_money_field_filled() -> None:
    assert s.is_field_filled({"receita": "1000"}, "receita") is True
    assert s.is_field_filled({"receita": ""}, "receita") is False
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
uv run pytest tests/unit/crm/test_stage_rules.py
```
Expected: FALHA.

- [ ] **Step 3: Implementar**

`src/modules/crm/domain/stage_rules.py`:
```python
import unicodedata

_MONEY = {"valor_tabela_fipe", "saldo_quitacao", "valor_pretendido", "valor_compra", "receita", "despesa", "rentabilidade"}
_SELECT_BOOL = {"tem_financiamento", "compareceu_agendamento"}

STAGE_FIELD_RULES: dict[str, dict] = {
    "RECEBIDOS": {"required": ["funil", "telefone"], "labels": {"funil": "Funil", "telefone": "Telefone"}},
    "CLASSIFICADOS": {"required": ["nome", "cidade"], "labels": {"nome": "Nome", "cidade": "Cidade"}},
    "QUALIFICADOS": {"required": ["modelo", "ano"], "labels": {"modelo": "Modelo do veículo", "ano": "Ano"}},
    "AGENDADOS": {"required": ["data_agendamento", "hora_agendamento"], "labels": {"data_agendamento": "Data", "hora_agendamento": "Horário"}},
    "EM ATENDIMENTO": {"required": ["compareceu_agendamento", "vendedor_id"], "labels": {"compareceu_agendamento": "Compareceu?", "vendedor_id": "Vendedor"}},
    "VEICULOS COMPRADOS": {"required": ["valor_compra"], "labels": {"valor_compra": "Valor de compra"}},
    "VEICULOS VENDIDOS": {"required": ["receita", "despesa", "rentabilidade"], "labels": {"receita": "Valor venda", "despesa": "Despesa", "rentabilidade": "Rentabilidade"}},
}


class StageRules:
    def normalize_stage_name(self, name: str | None) -> str:
        n = unicodedata.normalize("NFD", name or "")
        n = "".join(c for c in n if unicodedata.category(c) != "Mn")
        return n.upper().strip()

    def rules_for(self, stage_name: str | None) -> dict | None:
        return STAGE_FIELD_RULES.get(self.normalize_stage_name(stage_name))

    def is_em_atendimento(self, stage_name: str | None) -> bool:
        return self.normalize_stage_name(stage_name) == "EM ATENDIMENTO"

    def is_field_filled(self, lead: dict, key: str) -> bool:
        v = lead.get(key)
        if key in _MONEY:
            if v is None or v == "":
                return False
            if isinstance(v, (int, float)):
                return True
            return any(ch.isdigit() for ch in str(v))
        if key in _SELECT_BOOL:
            return v is True or v is False
        if key == "telefone":
            return any(ch.isdigit() for ch in str(v or ""))
        if key in ("funil", "hora_agendamento"):
            return v is not None and str(v).strip() != ""
        if isinstance(v, str):
            return v.strip() != ""
        return v is not None and v != ""

    def _missing_for_stage(self, lead: dict, rules: dict, stage_name: str | None) -> list[dict]:
        if self.is_em_atendimento(stage_name):
            if lead.get("compareceu_agendamento") is not True:
                return [{"field": "compareceu_agendamento", "label": rules["labels"]["compareceu_agendamento"]}]
            if not self.is_field_filled(lead, "vendedor_id"):
                return [{"field": "vendedor_id", "label": rules["labels"]["vendedor_id"]}]
            return []
        return [{"field": k, "label": rules["labels"].get(k, k)} for k in rules["required"] if not self.is_field_filled(lead, k)]

    def can_advance(self, stages: list[dict], from_index: int, to_index: int, lead: dict) -> tuple[bool, list[dict]]:
        missing: list[dict] = []
        if not stages or to_index <= from_index:
            return True, missing
        for i in range(from_index, to_index + 1):
            rules = self.rules_for(stages[i].get("name"))
            if not rules:
                continue
            for item in self._missing_for_stage(lead, rules, stages[i].get("name")):
                missing.append({"stage_name": stages[i].get("name"), **item})
        return len(missing) == 0, missing

    def compute_auto_stage_index(self, stages: list[dict], lead: dict) -> int:
        if not stages:
            return 0
        max_index = 0
        for i, stage in enumerate(stages):
            rules = self.rules_for(stage.get("name"))
            if not rules:
                if i == 0:
                    max_index = 0
                continue
            if not self._missing_for_stage(lead, rules, stage.get("name")):
                max_index = i
            elif i > 0:
                break
        return max_index
```

- [ ] **Step 4: Rodar e ver passar + commit**

```bash
uv run pytest tests/unit/crm/test_stage_rules.py
git add -A && git commit -m "feat(crm): port stage field rules"
```

---

## Task 2: Serviço de domínio `LeadPatch`

**Files:** `src/modules/crm/domain/lead_patch.py` + `tests/unit/crm/test_lead_patch.py`

- [ ] **Step 1: Teste**

`tests/unit/crm/test_lead_patch.py`:
```python
import re
from src.modules.crm.domain.lead_patch import LeadPatch

p = LeadPatch()


def test_agendamento_first_time() -> None:
    patch = p.agendamento({}, data_agendamento="2026-02-01", hora_agendamento="10:30", user_id="u1")
    assert patch["agendado_por"] == "u1"
    assert patch["hora_agendamento"] == "10:30:00"
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", patch["data_marcacao_agendamento"])


def test_agendamento_cleared() -> None:
    patch = p.agendamento({"agendado_por": "u", "data_marcacao_agendamento": "2026-01-01"}, data_agendamento="", hora_agendamento="", user_id="u")
    assert patch["agendado_por"] is None and patch["data_marcacao_agendamento"] is None


def test_compareceu() -> None:
    patch = p.compareceu({}, True)
    assert patch["compareceu_agendamento"] is True
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", patch["data_compareceu"])


def test_fechamento_money() -> None:
    patch = p.fechamento({}, receita="1.000,00", despesa="100,00", rentabilidade="900,00")
    assert patch["fechou_negocio"] is True
    assert patch["receita"] == 1000.0 and patch["despesa"] == 100.0 and patch["rentabilidade"] == 900.0
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/crm/domain/lead_patch.py`:
```python
import re
from datetime import date


def _today() -> str:
    return date.today().isoformat()


def parse_optional_money(s: str | None) -> float | None:
    if s is None or not any(ch.isdigit() for ch in str(s)):
        return None
    cleaned = re.sub(r"[^\d,]", "", str(s)).replace(",", ".")
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _has_digits(s: str | None) -> bool:
    return s is not None and any(ch.isdigit() for ch in str(s))


def _normalize_time(t: str | None) -> str | None:
    s = (t or "").strip()
    if re.match(r"^\d{2}:\d{2}$", s):
        return f"{s}:00"
    if re.match(r"^\d{2}:\d{2}:\d{2}", s):
        return s[:8]
    return None


class LeadPatch:
    def agendamento(self, prev: dict, data_agendamento: str | None, hora_agendamento: str | None, user_id: str | None) -> dict:
        data_ag = (data_agendamento or "").strip() or None
        hora_ag = _normalize_time(hora_agendamento)
        had = bool(prev.get("data_agendamento") and prev.get("hora_agendamento"))
        will = bool(data_ag and hora_ag)
        agendado_por = prev.get("agendado_por")
        if will and not had and user_id:
            agendado_por = user_id
        if not will:
            agendado_por = None
        marcacao = prev.get("data_marcacao_agendamento")
        if will:
            if not had:
                marcacao = _today()
            elif not marcacao and data_ag:
                marcacao = data_ag[:10]
        else:
            marcacao = None
        return {"data_agendamento": data_ag, "hora_agendamento": hora_ag, "agendado_por": agendado_por, "data_marcacao_agendamento": marcacao}

    def compareceu(self, prev: dict, compareceu: bool) -> dict:
        prev_comp = prev.get("compareceu_agendamento") is True
        data_comp = prev.get("data_compareceu")
        if compareceu is True and not prev_comp:
            data_comp = _today()
        if compareceu is not True:
            data_comp = None
        return {"compareceu_agendamento": compareceu, "data_compareceu": data_comp}

    def fechamento(self, prev: dict, receita: str | None, despesa: str | None, rentabilidade: str | None) -> dict:
        prev_fechou = prev.get("fechou_negocio") is True
        data_f = prev.get("data_fechou_negocio") if prev_fechou else _today()
        has_rd = _has_digits(receita) or _has_digits(despesa)
        return {
            "fechou_negocio": True, "data_fechou_negocio": data_f,
            "rentabilidade": parse_optional_money(rentabilidade),
            "receita": parse_optional_money(receita) if has_rd else None,
            "despesa": parse_optional_money(despesa) if has_rd else None,
        }
```

- [ ] **Step 3: Rodar e ver passar + commit**

```bash
uv run pytest tests/unit/crm/test_lead_patch.py
git add -A && git commit -m "feat(crm): port lead patch"
```

---

## Task 3: ORM do CRM + repositórios base

**Files:** `src/modules/crm/infrastructure/orm.py`, `repositories.py`

- [ ] **Step 1: ORM (mapeia o schema-alvo)**

`src/modules/crm/infrastructure/orm.py`:
```python
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class FunnelModel(Base):
    __tablename__ = "crm_funnels"
    id: Mapped[str] = mapped_column(primary_key=True)
    store_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    template_source_id: Mapped[str | None] = mapped_column(String, nullable=True)


class StageModel(Base):
    __tablename__ = "crm_funnel_stages"
    id: Mapped[str] = mapped_column(primary_key=True)
    funnel_id: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    template_stage_id: Mapped[str | None] = mapped_column(String, nullable=True)


class CoolingRuleModel(Base):
    __tablename__ = "crm_stage_cooling_rules"
    id: Mapped[str] = mapped_column(primary_key=True)
    stage_id: Mapped[str] = mapped_column(String)
    hours_threshold: Mapped[int] = mapped_column(Integer)
    card_color: Mapped[str] = mapped_column(String, default="#facc15")
    message: Mapped[str] = mapped_column(String, default="Lead esfriando")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class StageHistoryModel(Base):
    __tablename__ = "crm_lead_stage_history"
    id: Mapped[str] = mapped_column(primary_key=True)
    lead_id: Mapped[str] = mapped_column(String)
    stage_id: Mapped[str] = mapped_column(String)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ActivityModel(Base):
    __tablename__ = "crm_activity_log"
    id: Mapped[str] = mapped_column(primary_key=True)
    store_id: Mapped[str] = mapped_column(String)
    actor_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String)
    entity_type: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String, nullable=True)


class LeadModel(Base):
    __tablename__ = "crm_funnel_leads"
    id: Mapped[str] = mapped_column(primary_key=True)
    store_id: Mapped[str] = mapped_column(String)
    stage_id: Mapped[str] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    assigned_to: Mapped[str | None] = mapped_column(String, nullable=True)
    vendedor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    agendado_por: Mapped[str | None] = mapped_column(String, nullable=True)
    campaign_id: Mapped[str | None] = mapped_column(String, nullable=True)
    funil: Mapped[str | None] = mapped_column(String, nullable=True)
    qualificado: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    origem_mkt: Mapped[str | None] = mapped_column(String, nullable=True)
    urgencia_venda: Mapped[str | None] = mapped_column(String, nullable=True)
    nome: Mapped[str | None] = mapped_column(String, nullable=True)
    telefone: Mapped[str | None] = mapped_column(String, nullable=True)
    lid: Mapped[str | None] = mapped_column(String, nullable=True)
    bairro: Mapped[str | None] = mapped_column(String, nullable=True)
    cidade: Mapped[str | None] = mapped_column(String, nullable=True)
    modelo: Mapped[str | None] = mapped_column(String, nullable=True)
    veiculo: Mapped[str | None] = mapped_column(String, nullable=True)
    ano: Mapped[str | None] = mapped_column(String, nullable=True)
    cor: Mapped[str | None] = mapped_column(String, nullable=True)
    combustivel: Mapped[str | None] = mapped_column(String, nullable=True)
    quilometragem: Mapped[str | None] = mapped_column(String, nullable=True)
    transmissao: Mapped[str | None] = mapped_column(String, nullable=True)
    valor_tabela_fipe: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    tem_financiamento: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    saldo_quitacao: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    valor_pretendido: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    valor_compra: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    data_agendamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    hora_agendamento: Mapped[str | None] = mapped_column(String, nullable=True)
    data_marcacao_agendamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    compareceu_agendamento: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    data_compareceu: Mapped[date | None] = mapped_column(Date, nullable=True)
    fechou_negocio: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    data_fechou_negocio: Mapped[date | None] = mapped_column(Date, nullable=True)
    receita: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    despesa: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    rentabilidade: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Helper de conversão + repositórios de funil/etapa**

`src/modules/crm/infrastructure/repositories.py`:
```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.infrastructure.orm import (ActivityModel, CoolingRuleModel, FunnelModel, LeadModel, StageHistoryModel, StageModel)
from src.shared.domain.errors import NotFoundError


def lead_to_dict(r: LeadModel) -> dict:
    d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
    d["id"] = str(d["id"])
    for k in ("data_agendamento", "data_marcacao_agendamento", "data_compareceu", "data_fechou_negocio", "created_at", "updated_at"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    for k in ("valor_tabela_fipe", "saldo_quitacao", "valor_pretendido", "valor_compra", "receita", "despesa", "rentabilidade"):
        if d.get(k) is not None:
            d[k] = float(d[k])
    return d


class FunnelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_store(self, store_id: str) -> list[FunnelModel]:
        return list((await self._session.execute(select(FunnelModel).where(FunnelModel.store_id == store_id).order_by(FunnelModel.sort_order))).scalars().all())

    async def create(self, store_id: str | None, name: str, sort_order: int = 0, is_template: bool = False, template_source_id: str | None = None) -> FunnelModel:
        row = FunnelModel(id=str(uuid.uuid4()), store_id=store_id, name=name, sort_order=sort_order, is_template=is_template, template_source_id=template_source_id)
        self._session.add(row)
        await self._session.flush()
        return row

    async def first_template(self) -> FunnelModel | None:
        return (await self._session.execute(select(FunnelModel).where(FunnelModel.is_template.is_(True)).order_by(FunnelModel.sort_order).limit(1))).scalar_one_or_none()

    async def first_clone(self, store_id: str) -> FunnelModel | None:
        return (await self._session.execute(select(FunnelModel).where(FunnelModel.store_id == store_id, FunnelModel.template_source_id.isnot(None)).order_by(FunnelModel.sort_order).limit(1))).scalar_one_or_none()


class StageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_funnel(self, funnel_id: str) -> list[StageModel]:
        return list((await self._session.execute(select(StageModel).where(StageModel.funnel_id == funnel_id).order_by(StageModel.sort_order))).scalars().all())

    async def first_of_funnel(self, funnel_id: str) -> StageModel | None:
        return (await self._session.execute(select(StageModel).where(StageModel.funnel_id == funnel_id).order_by(StageModel.sort_order).limit(1))).scalar_one_or_none()

    async def get(self, stage_id: str) -> StageModel | None:
        return await self._session.get(StageModel, stage_id)

    async def create(self, funnel_id: str, name: str, sort_order: int = 0, template_stage_id: str | None = None) -> StageModel:
        row = StageModel(id=str(uuid.uuid4()), funnel_id=funnel_id, name=name, sort_order=sort_order, template_stage_id=template_stage_id)
        self._session.add(row)
        await self._session.flush()
        return row

    async def rename(self, stage_id: str, name: str) -> StageModel:
        row = await self._session.get(StageModel, stage_id)
        if row is None:
            raise NotFoundError("Etapa não encontrada")
        row.name = name
        await self._session.flush()
        return row
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat(crm): add orm models and funnel/stage repositories"
```

---

## Task 4: Funis & etapas — use cases + router

**Files:** `src/modules/crm/application/funnels.py`, `interface/{schemas.py,deps.py,router.py}`, `tests/unit/crm/test_funnel_use_cases.py`

- [ ] **Step 1: Use cases**

`src/modules/crm/application/funnels.py`:
```python
from src.modules.crm.infrastructure.repositories import FunnelRepository, StageRepository


class ListFunnelsUseCase:
    def __init__(self, funnels: FunnelRepository, stages: StageRepository) -> None:
        self._funnels = funnels
        self._stages = stages

    async def execute(self, store_id: str) -> list[dict]:
        out = []
        for f in await self._funnels.list_for_store(store_id):
            stages = await self._stages.list_for_funnel(f.id)
            out.append({"id": str(f.id), "name": f.name, "sort_order": f.sort_order,
                        "stages": [{"id": str(s.id), "name": s.name, "sort_order": s.sort_order} for s in stages]})
        return out


class CreateStageUseCase:
    def __init__(self, stages: StageRepository) -> None:
        self._stages = stages

    async def execute(self, funnel_id: str, name: str, sort_order: int) -> dict:
        s = await self._stages.create(funnel_id, name, sort_order)
        return {"id": str(s.id), "name": s.name, "sort_order": s.sort_order}


class RenameStageUseCase:
    def __init__(self, stages: StageRepository) -> None:
        self._stages = stages

    async def execute(self, stage_id: str, name: str) -> dict:
        s = await self._stages.rename(stage_id, name)
        return {"id": str(s.id), "name": s.name, "sort_order": s.sort_order}
```

- [ ] **Step 2: Schemas + deps + router**

`src/modules/crm/interface/schemas.py`:
```python
from pydantic import BaseModel


class CreateStageRequest(BaseModel):
    funnel_id: str
    name: str
    sort_order: int = 0


class RenameRequest(BaseModel):
    name: str
```
`src/modules/crm/interface/deps.py`:
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.application.funnels import CreateStageUseCase, ListFunnelsUseCase, RenameStageUseCase
from src.modules.crm.infrastructure.repositories import FunnelRepository, StageRepository
from src.shared.infrastructure.database import get_session


def get_list_funnels_uc(session: AsyncSession = Depends(get_session)) -> ListFunnelsUseCase:
    return ListFunnelsUseCase(FunnelRepository(session), StageRepository(session))


def get_create_stage_uc(session: AsyncSession = Depends(get_session)) -> CreateStageUseCase:
    return CreateStageUseCase(StageRepository(session))


def get_rename_stage_uc(session: AsyncSession = Depends(get_session)) -> RenameStageUseCase:
    return RenameStageUseCase(StageRepository(session))
```
`src/modules/crm/interface/router.py`:
```python
from fastapi import APIRouter, Depends, Query
from src.modules.crm.application.funnels import CreateStageUseCase, ListFunnelsUseCase, RenameStageUseCase
from src.modules.crm.interface.deps import get_create_stage_uc, get_list_funnels_uc, get_rename_stage_uc
from src.modules.crm.interface.schemas import CreateStageRequest, RenameRequest
from src.shared.interface.auth_deps import CurrentUser, get_current_user

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/funnels")
async def list_funnels(store_id: str = Query(...), _: CurrentUser = Depends(get_current_user), uc: ListFunnelsUseCase = Depends(get_list_funnels_uc)) -> list[dict]:
    return await uc.execute(store_id)


@router.post("/stages", status_code=201)
async def create_stage(body: CreateStageRequest, _: CurrentUser = Depends(get_current_user), uc: CreateStageUseCase = Depends(get_create_stage_uc)) -> dict:
    return await uc.execute(body.funnel_id, body.name, body.sort_order)


@router.patch("/stages/{stage_id}")
async def rename_stage(stage_id: str, body: RenameRequest, _: CurrentUser = Depends(get_current_user), uc: RenameStageUseCase = Depends(get_rename_stage_uc)) -> dict:
    return await uc.execute(stage_id, body.name)
```
Em `src/main.py`, inclua `from src.modules.crm.interface.router import router as crm_router` e `app.include_router(crm_router)`.

- [ ] **Step 3: Commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(crm): add funnels and stages endpoints"
```

---

## Task 5: Clone do funil-template (transação)

**Files:** `src/modules/crm/application/clone_template.py` + `tests/unit/crm/test_clone_template.py`

- [ ] **Step 1: Teste com repositórios fake**

`tests/unit/crm/test_clone_template.py`:
```python
import pytest
from src.modules.crm.application.clone_template import CloneTemplateUseCase


class FakeFunnels:
    def __init__(self): self.created = None
    async def first_template(self): return type("F", (), {"id": "tpl", "name": "Padrão"})()
    async def first_clone(self, store_id): return None
    async def create(self, store_id, name, sort_order=0, is_template=False, template_source_id=None):
        self.created = {"store_id": store_id, "name": name, "template_source_id": template_source_id}
        return type("F", (), {"id": "clone"})()


class FakeStages:
    async def list_for_funnel(self, fid): return [type("S", (), {"id": "s1", "name": "RECEBIDOS", "sort_order": 0})()]
    async def create(self, funnel_id, name, sort_order=0, template_stage_id=None): return type("S", (), {"id": "cs1"})()


class FakeCooling:
    async def list_for_stage(self, sid): return []
    async def copy(self, src, dst): ...


@pytest.mark.asyncio
async def test_clone_creates_funnel_and_stages() -> None:
    funnels = FakeFunnels()
    uc = CloneTemplateUseCase(funnels, FakeStages(), FakeCooling())
    out = await uc.execute("store-1")
    assert out["id"] == "clone"
    assert funnels.created["template_source_id"] == "tpl"
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/crm/application/clone_template.py`:
```python
from src.shared.domain.errors import NotFoundError


class CloneTemplateUseCase:
    def __init__(self, funnels, stages, cooling) -> None:
        self._funnels = funnels
        self._stages = stages
        self._cooling = cooling

    async def already_cloned(self, store_id: str) -> bool:
        return await self._funnels.first_clone(store_id) is not None

    async def execute(self, store_id: str) -> dict:
        tpl = await self._funnels.first_template()
        if tpl is None:
            raise NotFoundError("Nenhum funil-template configurado.")
        clone = await self._funnels.create(store_id, tpl.name, 0, False, tpl.id)
        for ts in await self._stages.list_for_funnel(tpl.id):
            new_stage = await self._stages.create(clone.id, ts.name, ts.sort_order, ts.id)
            await self._cooling.copy(ts.id, new_stage.id)
        return {"id": str(clone.id), "name": tpl.name}
```
> A `session` é única na requisição; o commit acontece no boundary (Plano 03 Task 6), então o clone é atômico. `CoolingRepository.copy` é criado na Task 8 — por ora o fake basta; ao integrar, injete o repositório real.

- [ ] **Step 3: Gancho no `UpdateStoreUseCase` (Plano 04)**

Em `src/modules/stores/application/update_store.py`, troque por:
```python
from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.ports import StoreRepository


class UpdateStoreUseCase:
    def __init__(self, stores: StoreRepository, clone_template=None) -> None:
        self._stores = stores
        self._clone = clone_template

    async def execute(self, store_id: str, data: dict[str, object]) -> Store:
        before = await self._stores.get_by_id(store_id)
        updated = await self._stores.update(store_id, data)
        if self._clone and data.get("crm_enabled") is True and (before is None or not before.crm_enabled) and not await self._clone.already_cloned(store_id):
            await self._clone.execute(store_id)
        return updated
```
Atualize `src/modules/stores/interface/deps.py` para injetar o `CloneTemplateUseCase` (com `FunnelRepository`, `StageRepository`, `CoolingRepository` da mesma session) no `get_update_store_uc`. Atualize o teste de stores para passar `clone_template=None` (comportamento sem clone preservado).

- [ ] **Step 4: Rodar e ver passar + commit**

```bash
uv run pytest tests/unit/crm/test_clone_template.py
git add -A && git commit -m "feat(crm): clone template funnel on crm enable"
```

---

## Task 6: Leads — repositório + CRUD

**Files:** `src/modules/crm/infrastructure/repositories.py` (LeadRepository), `application/leads.py`, `interface` (rotas).

- [ ] **Step 1: `LeadRepository` (adicione ao `repositories.py`)**

```python
class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_board(self, store_id: str, user) -> list[dict]:
        stmt = select(LeadModel).where(LeadModel.store_id == store_id)
        if getattr(user, "role", None) == "shop_user":
            stmt = stmt.where(LeadModel.assigned_to == user.user_id)
        stmt = stmt.order_by(LeadModel.stage_id, LeadModel.sort_order)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [lead_to_dict(r) for r in rows]

    async def get(self, lead_id: str) -> dict | None:
        r = await self._session.get(LeadModel, lead_id)
        return lead_to_dict(r) if r else None

    async def get_or_raise(self, lead_id: str) -> dict:
        d = await self.get(lead_id)
        if d is None:
            raise NotFoundError("Lead não encontrado")
        return d

    async def create(self, data: dict) -> dict:
        row = LeadModel(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return lead_to_dict(row)

    async def update(self, lead_id: str, data: dict) -> dict:
        row = await self._session.get(LeadModel, lead_id)
        if row is None:
            raise NotFoundError("Lead não encontrado")
        for k, v in data.items():
            setattr(row, k, v)
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return lead_to_dict(row)

    async def delete(self, lead_id: str) -> None:
        await self._session.execute(delete(LeadModel).where(LeadModel.id == lead_id))

    async def count_in_stage(self, stage_id: str) -> int:
        return int((await self._session.execute(select(func.count()).select_from(LeadModel).where(LeadModel.stage_id == stage_id))).scalar_one())
```

- [ ] **Step 2: Use cases + rotas + commit**

`src/modules/crm/application/leads.py`:
```python
class CreateLeadUseCase:
    def __init__(self, leads): self._leads = leads
    async def execute(self, data: dict) -> dict: return await self._leads.create(data)


class UpdateLeadUseCase:
    def __init__(self, leads): self._leads = leads
    async def execute(self, lead_id: str, data: dict) -> dict: return await self._leads.update(lead_id, data)


class ListLeadsUseCase:
    def __init__(self, leads): self._leads = leads
    async def execute(self, store_id: str, user) -> list[dict]: return await self._leads.list_for_board(store_id, user)


class DeleteLeadUseCase:
    def __init__(self, leads): self._leads = leads
    async def execute(self, lead_id: str) -> None: await self._leads.delete(lead_id)
```
Adicione ao `crm/interface/router.py` as rotas `GET /crm/leads?store_id=` (passa `user`), `POST /crm/leads`, `PATCH /crm/leads/{id}`, `DELETE /crm/leads/{id}` — com `Depends(get_current_user)` e providers em `deps.py` (no padrão das Tasks anteriores: `LeadRepository(session)`). Schemas: `CreateLeadRequest` (store_id, stage_id, funil, nome, telefone, cidade, modelo, ano, assigned_to — todos opcionais exceto store_id/stage_id) e `UpdateLeadRequest` (campos editáveis opcionais).
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(crm): add leads crud"
```

---

## Task 7: Mover de coluna (validação + histórico + atividade)

**Files:** `src/modules/crm/infrastructure/repositories.py` (HistoryRepository, ActivityRepository), `application/move_lead.py` + teste.

- [ ] **Step 1: Repositórios de histórico/atividade (adicione ao `repositories.py`)**

```python
class HistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, lead_id: str, stage_id: str) -> None:
        self._session.add(StageHistoryModel(id=str(uuid.uuid4()), lead_id=lead_id, stage_id=stage_id))
        await self._session.flush()


class ActivityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(self, store_id: str, actor_user_id: str | None, action: str, entity_type: str | None = None, entity_id: str | None = None) -> None:
        self._session.add(ActivityModel(id=str(uuid.uuid4()), store_id=store_id, actor_user_id=actor_user_id, action=action, entity_type=entity_type, entity_id=entity_id))
        await self._session.flush()
```

- [ ] **Step 2: Teste do use case (fakes)**

`tests/unit/crm/test_move_lead.py`:
```python
import pytest
from src.modules.crm.application.move_lead import MoveLeadStageUseCase
from src.modules.crm.domain.stage_rules import StageRules
from src.shared.domain.errors import DomainError


class FakeLeads:
    def __init__(self, lead): self.lead = lead; self.moved_to = None
    async def get_or_raise(self, lead_id): return self.lead
    async def update(self, lead_id, data): self.moved_to = data["stage_id"]; return {**self.lead, **data}


class FakeStages:
    def __init__(self, stages): self.stages = stages
    async def get(self, sid): return next(s for s in self.stages if s["id"] == sid)
    async def list_for_funnel(self, fid): return [type("S", (), s)() for s in self.stages]


class FakeHistory:
    def __init__(self): self.recorded = None
    async def record(self, lead_id, stage_id): self.recorded = (lead_id, stage_id)


class FakeActivity:
    async def log(self, **kw): ...


class U:
    user_id = "u1"; role = "client"


STAGES = [{"id": "st0", "name": "RECEBIDOS", "funnel_id": "f1", "sort_order": 0},
          {"id": "st1", "name": "CLASSIFICADOS", "funnel_id": "f1", "sort_order": 1}]


@pytest.mark.asyncio
async def test_blocks_without_required_fields() -> None:
    leads = FakeLeads({"id": "l1", "store_id": "s1", "stage_id": "st0", "funil": "r", "telefone": "1"})
    uc = MoveLeadStageUseCase(leads, FakeStages(STAGES), FakeHistory(), FakeActivity(), StageRules())
    with pytest.raises(DomainError):
        await uc.execute("l1", "st1", U())


@pytest.mark.asyncio
async def test_moves_with_fields() -> None:
    leads = FakeLeads({"id": "l1", "store_id": "s1", "stage_id": "st0", "funil": "r", "telefone": "1", "nome": "A", "cidade": "C"})
    hist = FakeHistory()
    uc = MoveLeadStageUseCase(leads, FakeStages(STAGES), hist, FakeActivity(), StageRules())
    await uc.execute("l1", "st1", U())
    assert leads.moved_to == "st1"
    assert hist.recorded == ("l1", "st1")
```

- [ ] **Step 3: Rodar e ver falhar → implementar**

`src/modules/crm/application/move_lead.py`:
```python
from src.modules.crm.domain.stage_rules import StageRules
from src.shared.domain.errors import DomainError


class MoveLeadStageUseCase:
    def __init__(self, leads, stages, history, activity, rules: StageRules) -> None:
        self._leads = leads
        self._stages = stages
        self._history = history
        self._activity = activity
        self._rules = rules

    async def execute(self, lead_id: str, to_stage_id: str, user) -> dict:
        lead = await self._leads.get_or_raise(lead_id)
        target = await self._stages.get(to_stage_id)
        if target is None:
            raise DomainError("Etapa de destino inválida.")
        ordered = await self._stages.list_for_funnel(target.funnel_id)
        ids = [str(s.id) for s in ordered]
        from_i = ids.index(str(lead["stage_id"])) if str(lead["stage_id"]) in ids else -1
        to_i = ids.index(to_stage_id)
        if to_i > from_i:
            stages_for_rules = [{"name": s.name} for s in ordered]
            ok, missing = self._rules.can_advance(stages_for_rules, from_i, to_i, lead)
            if not ok:
                labels = ", ".join(dict.fromkeys(m["label"] for m in missing))
                raise DomainError(f"Preencha os campos obrigatórios: {labels}.")
        moved = await self._leads.update(lead_id, {"stage_id": to_stage_id})
        await self._history.record(lead_id, to_stage_id)
        await self._activity.log(store_id=lead["store_id"], actor_user_id=user.user_id, action="lead_moved", entity_type="lead", entity_id=lead_id)
        return moved
```
> No teste, `FakeStages.get` retorna um dict (com `.funnel_id`? não). Ajuste: no use case use `target["funnel_id"]` se `get` retornar dict, ou faça `get` retornar objeto. **Decisão:** `StageRepository.get` retorna `StageModel` (objeto com `.funnel_id`/`.name`); o `FakeStages.get` do teste deve retornar um objeto — troque o teste para `return type("S", (), next(...))()`. (Mantenha objeto, não dict, para consistência com o repositório real.)

- [ ] **Step 4: Rota + commit**

Adicione `PATCH /crm/leads/{id}/stage` (body `{"to_stage_id": ...}`) com provider que monta `MoveLeadStageUseCase(LeadRepository, StageRepository, HistoryRepository, ActivityRepository, StageRules())`.
```bash
uv run pytest tests/unit/crm/test_move_lead.py
git add -A && git commit -m "feat(crm): move lead with validation, history and activity"
```

---

## Task 8: Patches + Cooling

**Files:** `src/modules/crm/application/patches.py`, `domain/cooling.py`, `infrastructure/repositories.py` (CoolingRepository), rotas + testes.

- [ ] **Step 1: Use cases de patch**

`src/modules/crm/application/patches.py`:
```python
from src.modules.crm.domain.lead_patch import LeadPatch


class SetAgendamentoUseCase:
    def __init__(self, leads, patch: LeadPatch): self._leads = leads; self._patch = patch
    async def execute(self, lead_id, data_agendamento, hora_agendamento, user) -> dict:
        prev = await self._leads.get_or_raise(lead_id)
        return await self._leads.update(lead_id, self._patch.agendamento(prev, data_agendamento, hora_agendamento, user.user_id))


class SetCompareceuUseCase:
    def __init__(self, leads, patch: LeadPatch): self._leads = leads; self._patch = patch
    async def execute(self, lead_id, compareceu) -> dict:
        prev = await self._leads.get_or_raise(lead_id)
        return await self._leads.update(lead_id, self._patch.compareceu(prev, compareceu))


class SetFechamentoUseCase:
    def __init__(self, leads, patch: LeadPatch): self._leads = leads; self._patch = patch
    async def execute(self, lead_id, receita, despesa, rentabilidade) -> dict:
        prev = await self._leads.get_or_raise(lead_id)
        return await self._leads.update(lead_id, self._patch.fechamento(prev, receita, despesa, rentabilidade))
```
> As chaves dos patches já estão em snake_case = nomes das colunas do `LeadModel`, então `leads.update(...)` aplica direto.

- [ ] **Step 2: Cooling (domínio + repo)**

`src/modules/crm/domain/cooling.py`:
```python
class Cooling:
    def active_rule(self, hours_in_column: float, rules: list[dict]) -> dict | None:
        active = None
        for r in rules or []:
            if hours_in_column >= r["hours_threshold"]:
                active = r
        return active
```
Adicione ao `repositories.py`:
```python
class CoolingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_stage(self, stage_id: str) -> list[dict]:
        rows = (await self._session.execute(select(CoolingRuleModel).where(CoolingRuleModel.stage_id == stage_id).order_by(CoolingRuleModel.hours_threshold))).scalars().all()
        return [{"id": str(r.id), "hours_threshold": r.hours_threshold, "card_color": r.card_color, "message": r.message, "sort_order": r.sort_order} for r in rows]

    async def save(self, stage_id: str, rules: list[dict]) -> list[dict]:
        await self._session.execute(delete(CoolingRuleModel).where(CoolingRuleModel.stage_id == stage_id))
        for i, r in enumerate(rules or []):
            self._session.add(CoolingRuleModel(id=str(uuid.uuid4()), stage_id=stage_id, hours_threshold=r["hours_threshold"], card_color=r.get("card_color") or "#facc15", message=r.get("message") or "Lead esfriando", sort_order=i))
        await self._session.flush()
        return await self.list_for_stage(stage_id)

    async def copy(self, src_stage_id: str, dst_stage_id: str) -> None:
        rules = await self.list_for_stage(src_stage_id)
        if rules:
            await self.save(dst_stage_id, rules)
```
Teste `tests/unit/crm/test_cooling.py`: `Cooling().active_rule(50, [{"hours_threshold":24},{"hours_threshold":48}])["hours_threshold"] == 48`; `active_rule(10, ...) is None`.

- [ ] **Step 3: Rotas + commit + concluir**

Adicione rotas: `PATCH /crm/leads/{id}/agendamento|comparecimento|fechamento` (providers montam o use case com `LeadRepository` + `LeadPatch()`); `PUT /crm/stages/{id}/cooling-rules` (body lista de regras → `CoolingRepository.save`).
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(crm): add patches and cooling rules"
```
Atualize o status do Plano 05 para ✅ em [`00-INDEX.md`](./00-INDEX.md).

---

## Resultado

- CRM completo via API hexagonal, com regras e patches como serviços de domínio testados, clone de template, validação de avanço, histórico, cooling e atividade — código copia-e-cola.

**Próximo:** [`06-webhook-zapi.md`](./06-webhook-zapi.md).
