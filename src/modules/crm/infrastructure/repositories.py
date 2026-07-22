import uuid
from datetime import date, datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.domain.lead_patch import parse_optional_money
from src.modules.crm.infrastructure.orm import (
    ActivityModel,
    CoolingRuleModel,
    FunnelModel,
    LeadModel,
    StageHistoryModel,
    StageModel,
)
from src.shared.domain.errors import DomainError, NotFoundError


def lead_to_dict(r: LeadModel) -> dict[str, object]:
    d: dict[str, object] = {c.name: getattr(r, c.name) for c in r.__table__.columns}
    d["id"] = str(d["id"])
    for k in ("data_agendamento", "data_marcacao_agendamento", "data_compareceu", "data_fechou_negocio", "data_comprado", "created_at", "updated_at"):
        v = d.get(k)
        if v is not None and hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    for k in ("valor_tabela_fipe", "saldo_quitacao", "valor_pretendido", "valor_compra", "receita", "despesa", "rentabilidade"):
        if d.get(k) is not None:
            d[k] = float(d[k])  # type: ignore[arg-type]
    return d


_DATE_FIELDS = ("data_agendamento", "data_marcacao_agendamento", "data_compareceu", "data_fechou_negocio", "data_comprado")
_MONEY_FIELDS = ("valor_tabela_fipe", "saldo_quitacao", "valor_pretendido", "valor_compra", "receita", "despesa", "rentabilidade")


_MAX_NUMERIC = 10 ** 12  # NUMERIC(14,2): 12 dígitos antes da vírgula


def _is_uuid(v: object) -> bool:
    try:
        uuid.UUID(str(v))
    except (ValueError, AttributeError, TypeError):
        return False
    return True


def _coerce_dates(data: dict[str, object]) -> dict[str, object]:
    """Colunas DATE exigem datetime.date e NUMERIC exige número no asyncpg;
    API/domínio trafegam strings ("2026-07-20", "85.000,00"). Input inválido
    vira erro de domínio (400), nunca 500."""
    out = dict(data)
    for k in _DATE_FIELDS:
        v = out.get(k)
        if isinstance(v, str) and v:
            try:
                out[k] = date.fromisoformat(v[:10])
            except ValueError as exc:
                raise DomainError(f"Data inválida em '{k}': use AAAA-MM-DD.") from exc
    for k in _MONEY_FIELDS:
        v = out.get(k)
        if isinstance(v, str):
            n = parse_optional_money(v)
            if n is not None and abs(n) >= _MAX_NUMERIC:
                raise DomainError(f"Valor de '{k}' fora da faixa suportada.")
            out[k] = n
    return out


class FunnelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_store(self, store_id: str) -> list[FunnelModel]:
        return list((await self._session.execute(
            select(FunnelModel).where(FunnelModel.store_id == store_id).order_by(FunnelModel.sort_order)
        )).scalars().all())

    async def create(
        self, store_id: str | None, name: str, sort_order: int = 0, is_template: bool = False, template_source_id: str | None = None
    ) -> FunnelModel:
        row = FunnelModel(id=str(uuid.uuid4()), store_id=store_id, name=name, sort_order=sort_order, is_template=is_template, template_source_id=template_source_id)
        self._session.add(row)
        await self._session.flush()
        return row

    async def first_template(self) -> FunnelModel | None:
        return (await self._session.execute(
            select(FunnelModel).where(FunnelModel.is_template.is_(True)).order_by(FunnelModel.sort_order).limit(1)
        )).scalar_one_or_none()

    async def first_clone(self, store_id: str) -> FunnelModel | None:
        return (await self._session.execute(
            select(FunnelModel).where(FunnelModel.store_id == store_id, FunnelModel.template_source_id.isnot(None)).order_by(FunnelModel.sort_order).limit(1)
        )).scalar_one_or_none()

    async def get(self, funnel_id: str) -> FunnelModel | None:
        return await self._session.get(FunnelModel, funnel_id)

    async def list_templates(self) -> list[FunnelModel]:
        return list((await self._session.execute(
            select(FunnelModel).where(FunnelModel.is_template.is_(True)).order_by(FunnelModel.sort_order)
        )).scalars().all())

    async def list_clones(self, template_id: str) -> list[FunnelModel]:
        return list((await self._session.execute(
            select(FunnelModel).where(FunnelModel.template_source_id == template_id)
        )).scalars().all())

    async def update_name(self, funnel_id: str, name: str) -> None:
        row = await self._session.get(FunnelModel, funnel_id)
        if row is not None:
            row.name = name
            await self._session.flush()


class StageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_funnel(self, funnel_id: str) -> list[StageModel]:
        return list((await self._session.execute(
            select(StageModel).where(StageModel.funnel_id == funnel_id).order_by(StageModel.sort_order)
        )).scalars().all())

    async def first_of_funnel(self, funnel_id: str) -> StageModel | None:
        return (await self._session.execute(
            select(StageModel).where(StageModel.funnel_id == funnel_id).order_by(StageModel.sort_order).limit(1)
        )).scalar_one_or_none()

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


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_board(
        self,
        store_id: str,
        *,
        restrict_to_user: str | None = None,
        include_unassigned: bool = False,
        assigned_to: str | None = None,
    ) -> list[dict[str, object]]:
        """Lista os leads do quadro com visibilidade + filtro opcional por responsável.

        Visibilidade (espelha o legado): quando ``restrict_to_user`` é informado, o usuário
        só vê os próprios leads — e, se ``include_unassigned``, também os não atribuídos.
        Gerente/dono/admin recebem ``restrict_to_user=None`` (veem o funil inteiro da loja).
        ``assigned_to`` é um filtro adicional (id do responsável ou ``"__unassigned__"``) que
        apenas restringe dentro do que já é visível — nunca amplia o acesso.
        """
        stmt = select(LeadModel).where(LeadModel.store_id == store_id)
        if restrict_to_user is not None:
            if include_unassigned:
                stmt = stmt.where(or_(LeadModel.assigned_to == restrict_to_user, LeadModel.assigned_to.is_(None)))
            else:
                stmt = stmt.where(LeadModel.assigned_to == restrict_to_user)
        if assigned_to == "__unassigned__":
            stmt = stmt.where(LeadModel.assigned_to.is_(None))
        elif assigned_to:
            stmt = stmt.where(LeadModel.assigned_to == assigned_to)
        stmt = stmt.order_by(LeadModel.stage_id, LeadModel.sort_order)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [lead_to_dict(r) for r in rows]

    async def get(self, lead_id: str) -> dict[str, object] | None:
        if not _is_uuid(lead_id):
            return None
        r = await self._session.get(LeadModel, lead_id)
        return lead_to_dict(r) if r else None

    async def get_or_raise(self, lead_id: str) -> dict[str, object]:
        d = await self.get(lead_id)
        if d is None:
            raise NotFoundError("Lead não encontrado")
        return d

    async def create(self, data: dict[str, object]) -> dict[str, object]:
        row = LeadModel(id=str(uuid.uuid4()), **_coerce_dates(data))
        self._session.add(row)
        await self._session.flush()
        return lead_to_dict(row)

    async def update(self, lead_id: str, data: dict[str, object]) -> dict[str, object]:
        if not _is_uuid(lead_id):
            raise NotFoundError("Lead não encontrado")
        row = await self._session.get(LeadModel, lead_id)
        if row is None:
            raise NotFoundError("Lead não encontrado")
        for k, v in _coerce_dates(data).items():
            setattr(row, k, v)
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return lead_to_dict(row)

    async def delete(self, lead_id: str) -> None:
        if not _is_uuid(lead_id):
            raise NotFoundError("Lead não encontrado")
        await self._session.execute(delete(LeadModel).where(LeadModel.id == lead_id))

    async def count_in_stage(self, stage_id: str) -> int:
        return int((await self._session.execute(
            select(func.count()).select_from(LeadModel).where(LeadModel.stage_id == stage_id)
        )).scalar_one())

    async def move_all_from_stage(self, from_stage_id: str, to_stage_id: str) -> None:
        from sqlalchemy import update as _update
        await self._session.execute(_update(LeadModel).where(LeadModel.stage_id == from_stage_id).values(stage_id=to_stage_id))


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


class CoolingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_stage(self, stage_id: str) -> list[dict[str, object]]:
        rows = (await self._session.execute(
            select(CoolingRuleModel).where(CoolingRuleModel.stage_id == stage_id).order_by(CoolingRuleModel.hours_threshold)
        )).scalars().all()
        return [{"id": str(r.id), "hours_threshold": r.hours_threshold, "card_color": r.card_color, "message": r.message, "sort_order": r.sort_order} for r in rows]

    async def save(self, stage_id: str, rules: list[dict[str, object]]) -> list[dict[str, object]]:
        await self._session.execute(delete(CoolingRuleModel).where(CoolingRuleModel.stage_id == stage_id))
        for i, r in enumerate(rules or []):
            self._session.add(CoolingRuleModel(
                id=str(uuid.uuid4()), stage_id=stage_id,
                hours_threshold=int(str(r["hours_threshold"])),
                card_color=str(r.get("card_color") or "#facc15"),
                message=str(r.get("message") or "Lead esfriando"),
                sort_order=i,
            ))
        await self._session.flush()
        return await self.list_for_stage(stage_id)

    async def copy(self, src_stage_id: str, dst_stage_id: str) -> None:
        rules = await self.list_for_stage(src_stage_id)
        if rules:
            await self.save(dst_stage_id, rules)

    async def delete_for_stage(self, stage_id: str) -> None:
        await self._session.execute(delete(CoolingRuleModel).where(CoolingRuleModel.stage_id == stage_id))
