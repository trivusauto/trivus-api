# Plano 05b — Funis-template do admin (CRUD + sync para clientes)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 05. Fecha a lacuna do `admin/crm`. Código copia-e-cola.

**Goal:** Admin cria/edita **funis-template** (`is_template=true`) e, ao salvar, **propaga** as mudanças para todos os funis clonados dos clientes (`syncTemplateFunnelToClients`, spec §6.9) — renomeia, cria etapas novas, move leads de etapas órfãs para um fallback e remove órfãs, preservando cooling rules.

**Architecture:** Estende o módulo `crm` com repositórios adicionais e o use case de sync. Tudo na mesma `session` (transação da requisição).

---

## Task 1: Métodos de repositório adicionais

**Files:** Modify `src/modules/crm/infrastructure/repositories.py`

- [ ] **Step 1: Estender `FunnelRepository`, `StageRepository`, `CoolingRepository`, `LeadRepository`**

Adicione ao `FunnelRepository`:
```python
    async def get(self, funnel_id: str) -> FunnelModel | None:
        return await self._session.get(FunnelModel, funnel_id)

    async def list_templates(self) -> list[FunnelModel]:
        return list((await self._session.execute(select(FunnelModel).where(FunnelModel.is_template.is_(True)).order_by(FunnelModel.sort_order))).scalars().all())

    async def list_clones(self, template_id: str) -> list[FunnelModel]:
        return list((await self._session.execute(select(FunnelModel).where(FunnelModel.template_source_id == template_id))).scalars().all())

    async def update_name(self, funnel_id: str, name: str) -> None:
        row = await self._session.get(FunnelModel, funnel_id)
        if row is not None:
            row.name = name
            await self._session.flush()
```
Adicione ao `StageRepository`:
```python
    async def update(self, stage_id: str, name: str | None = None, sort_order: int | None = None, template_stage_id: str | None = None) -> None:
        row = await self._session.get(StageModel, stage_id)
        if row is None:
            return
        if name is not None:
            row.name = name
        if sort_order is not None:
            row.sort_order = sort_order
        if template_stage_id is not None:
            row.template_stage_id = template_stage_id
        await self._session.flush()

    async def delete(self, stage_id: str) -> None:
        from sqlalchemy import delete as _delete
        await self._session.execute(_delete(StageModel).where(StageModel.id == stage_id))
```
Adicione ao `CoolingRepository`:
```python
    async def delete_for_stage(self, stage_id: str) -> None:
        await self._session.execute(delete(CoolingRuleModel).where(CoolingRuleModel.stage_id == stage_id))
```
Adicione ao `LeadRepository`:
```python
    async def move_all_from_stage(self, from_stage_id: str, to_stage_id: str) -> None:
        from sqlalchemy import update as _update
        await self._session.execute(_update(LeadModel).where(LeadModel.stage_id == from_stage_id).values(stage_id=to_stage_id))
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat(crm): add repository methods for template sync"
```

---

## Task 2: Template CRUD

**Files:** `src/modules/crm/application/templates_crud.py`, rotas no `interface`.

- [ ] **Step 1: Use cases**

`src/modules/crm/application/templates_crud.py`:
```python
class ListTemplatesUseCase:
    def __init__(self, funnels, stages) -> None:
        self._funnels = funnels
        self._stages = stages

    async def execute(self) -> list[dict]:
        out = []
        for f in await self._funnels.list_templates():
            stages = await self._stages.list_for_funnel(f.id)
            out.append({"id": str(f.id), "name": f.name, "sort_order": f.sort_order,
                        "stages": [{"id": str(s.id), "name": s.name, "sort_order": s.sort_order} for s in stages]})
        return out


class CreateTemplateUseCase:
    def __init__(self, funnels, stages) -> None:
        self._funnels = funnels
        self._stages = stages

    async def execute(self, name: str, stage_names: list[str]) -> dict:
        funnel = await self._funnels.create(None, name, 0, True, None)
        for i, sn in enumerate(stage_names):
            await self._stages.create(funnel.id, sn, i, None)
        return {"id": str(funnel.id), "name": name}
```

- [ ] **Step 2: Rotas + commit**

Adicione ao `crm/interface/router.py` (`require_roles("admin")`): `GET /admin/crm/templates` (ListTemplates), `POST /admin/crm/templates` (body `{"name": str, "stages": [str]}` → CreateTemplate). Providers em `deps.py` no padrão do Plano 05.
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(crm): add template funnels crud"
```

---

## Task 3: `SyncTemplateToClientsUseCase` (o port de `syncTemplateFunnelToClients`)

**Files:** `src/modules/crm/application/sync_template.py` + `tests/unit/crm/test_sync_template.py`

- [ ] **Step 1: Teste com fakes (cria etapa nova + remove órfã movendo leads)**

`tests/unit/crm/test_sync_template.py`:
```python
import pytest
from src.modules.crm.application.sync_template import SyncTemplateToClientsUseCase


def stage(sid, name, order, tsid=None):
    return type("S", (), {"id": sid, "name": name, "sort_order": order, "template_stage_id": tsid})()


class FakeFunnels:
    def __init__(self):
        self.tpl = type("F", (), {"id": "tpl", "name": "Padrão Novo"})()
        self.clone = type("F", (), {"id": "cl", "name": "Antigo", "template_source_id": "tpl"})()
        self.renamed = None
    async def list_clones(self, template_id): return [self.clone]
    async def get(self, fid): return self.tpl if fid == "tpl" else self.clone
    async def update_name(self, fid, name): self.renamed = name


class FakeStages:
    def __init__(self):
        self.tpl_stages = [stage("t1", "RECEBIDOS", 0), stage("t2", "CLASSIFICADOS", 1)]
        self.client_stages = [stage("c1", "RECEBIDOS", 0, "t1"), stage("c9", "COLUNA ANTIGA", 1, None)]
        self.created = []
        self.deleted = []
        self.updated = []
    async def list_for_funnel(self, fid):
        return self.tpl_stages if fid == "tpl" else self.client_stages
    async def create(self, funnel_id, name, sort_order=0, template_stage_id=None):
        s = stage(f"new-{name}", name, sort_order, template_stage_id)
        self.created.append(s); self.client_stages.append(s); return s
    async def update(self, stage_id, name=None, sort_order=None, template_stage_id=None):
        self.updated.append(stage_id)
        for s in self.client_stages:
            if s.id == stage_id and template_stage_id is not None:
                s.template_stage_id = template_stage_id
    async def delete(self, stage_id):
        self.deleted.append(stage_id)
        self.client_stages = [s for s in self.client_stages if s.id != stage_id]


class FakeCooling:
    async def copy(self, src, dst): ...
    async def delete_for_stage(self, sid): ...


class FakeLeads:
    def __init__(self): self.moves = []
    async def move_all_from_stage(self, frm, to): self.moves.append((frm, to))


@pytest.mark.asyncio
async def test_sync_creates_and_removes_orphan() -> None:
    funnels, stages, leads = FakeFunnels(), FakeStages(), FakeLeads()
    uc = SyncTemplateToClientsUseCase(funnels, stages, FakeCooling(), leads)
    await uc.execute("tpl")
    assert funnels.renamed == "Padrão Novo"
    assert any(s.name == "CLASSIFICADOS" for s in stages.created)   # etapa nova criada
    assert "c9" in stages.deleted                                    # órfã removida
    assert leads.moves and leads.moves[0][0] == "c9"                 # leads movidos p/ fallback
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/crm/application/sync_template.py`:
```python
class SyncTemplateToClientsUseCase:
    def __init__(self, funnels, stages, cooling, leads) -> None:
        self._funnels = funnels
        self._stages = stages
        self._cooling = cooling
        self._leads = leads

    async def execute(self, template_id: str) -> None:
        for clone in await self._funnels.list_clones(template_id):
            await self._sync_one(clone)

    async def _backfill_template_ids(self, tpl_stages, client_stages) -> None:
        sorted_tpl = sorted(tpl_stages, key=lambda s: s.sort_order or 0)
        sorted_client = sorted(client_stages, key=lambda s: s.sort_order or 0)
        claimed = {str(s.template_stage_id) for s in client_stages if s.template_stage_id}
        for i, cs in enumerate(sorted_client):
            if cs.template_stage_id and str(cs.template_stage_id) in claimed:
                continue
            if i >= len(sorted_tpl):
                break
            ts = sorted_tpl[i]
            if str(ts.id) in claimed:
                continue
            await self._stages.update(cs.id, template_stage_id=str(ts.id))
            claimed.add(str(ts.id))

    async def _sync_one(self, clone) -> None:
        tpl = await self._funnels.get(clone.template_source_id)
        if tpl is None:
            return
        await self._funnels.update_name(clone.id, tpl.name)

        tpl_stages = await self._stages.list_for_funnel(tpl.id)
        client_stages = await self._stages.list_for_funnel(clone.id)
        await self._backfill_template_ids(tpl_stages, client_stages)

        client_stages = await self._stages.list_for_funnel(clone.id)
        tpl_stage_ids = {str(s.id) for s in tpl_stages}
        by_template_id = {str(cs.template_stage_id): cs for cs in client_stages if cs.template_stage_id}

        first_client_stage_id = None
        for ts in tpl_stages:
            existing = by_template_id.get(str(ts.id))
            if existing is not None:
                await self._stages.update(existing.id, name=ts.name, sort_order=ts.sort_order)
                await self._cooling.copy(ts.id, existing.id)
                if first_client_stage_id is None:
                    first_client_stage_id = existing.id
            else:
                new_stage = await self._stages.create(clone.id, ts.name, ts.sort_order, str(ts.id))
                await self._cooling.copy(ts.id, new_stage.id)
                if first_client_stage_id is None:
                    first_client_stage_id = new_stage.id

        client_stages = await self._stages.list_for_funnel(clone.id)
        fallback = first_client_stage_id
        if fallback is None:
            fallback = next((s.id for s in client_stages if s.template_stage_id and str(s.template_stage_id) in tpl_stage_ids), None)
        if fallback is None and client_stages:
            fallback = client_stages[0].id

        orphans = [cs for cs in client_stages if not cs.template_stage_id or str(cs.template_stage_id) not in tpl_stage_ids]
        for orphan in orphans:
            if fallback and orphan.id != fallback:
                await self._leads.move_all_from_stage(orphan.id, fallback)
            await self._cooling.delete_for_stage(orphan.id)
            await self._stages.delete(orphan.id)
```
```bash
uv run pytest tests/unit/crm/test_sync_template.py
```
Expected: PASSA.

- [ ] **Step 3: Disparar o sync ao salvar o template + commit + concluir**

Adicione uma rota `POST /admin/crm/templates/{id}/sync` (`require_roles("admin")`) que monta `SyncTemplateToClientsUseCase(FunnelRepository, StageRepository, CoolingRepository, LeadRepository)` e chama `.execute(id)`. (Opcionalmente, chame o sync também dentro do endpoint de edição do template.)
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(crm): sync template funnel to client clones"
```
Adicione a linha do Plano 05b em [`00-INDEX.md`](./00-INDEX.md) e marque ✅ ao concluir.

---

## Resultado

- Admin gerencia funis-template e propaga mudanças para os clientes com segurança (leads de etapas removidas migram para o fallback). Fecha a lacuna do `admin/crm`.

Com 05b + 08b, a **cobertura do frontend está completa**.
