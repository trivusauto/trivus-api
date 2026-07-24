"""Leituras agregadas do Painel Executivo (S4.11).

Tudo por loja em UMA query com GROUP BY — o painel é multi-loja por natureza e
não pode fazer uma consulta por unidade.
"""
from datetime import date

from sqlalchemy import Integer, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.infrastructure.orm import LeadModel
from src.modules.indicators.infrastructure.orm import DailyIndicatorModel


class ExecutiveReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def closings_by_store(
        self, store_ids: list[str], start: str, end: str
    ) -> dict[str, dict[str, float]]:
        """Fechamentos do mês por loja: receita, rentabilidade e contagem."""
        if not store_ids:
            return {}
        stmt = (
            select(
                LeadModel.store_id,
                func.coalesce(func.sum(LeadModel.receita), 0),
                func.coalesce(func.sum(LeadModel.rentabilidade), 0),
                func.count(),
            )
            .where(
                LeadModel.store_id.in_(store_ids),
                LeadModel.fechou_negocio.is_(True),
                LeadModel.data_fechou_negocio >= date.fromisoformat(start),
                LeadModel.data_fechou_negocio <= date.fromisoformat(end),
            )
            .group_by(LeadModel.store_id)
        )
        return {
            str(sid): {
                "receita": float(receita or 0),
                "rentabilidade": float(rentabilidade or 0),
                "fechamentos": float(qtd or 0),
            }
            for sid, receita, rentabilidade, qtd in (await self._session.execute(stmt)).all()
        }

    async def vehicle_counts_by_store(
        self, store_ids: list[str], start: str, end: str
    ) -> dict[str, dict[str, int]]:
        """Comprados (`data_comprado`) × vendidos (`data_fechou_negocio`) no mês."""
        if not store_ids:
            return {}
        d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
        comprado = case((LeadModel.data_comprado.between(d0, d1), 1), else_=0)
        vendido = case(
            (LeadModel.data_fechou_negocio.between(d0, d1) & LeadModel.fechou_negocio.is_(True), 1),
            else_=0,
        )
        stmt = (
            select(
                LeadModel.store_id,
                func.coalesce(func.sum(comprado.cast(Integer)), 0),
                func.coalesce(func.sum(vendido.cast(Integer)), 0),
            )
            .where(LeadModel.store_id.in_(store_ids))
            .group_by(LeadModel.store_id)
        )
        return {
            str(sid): {"comprados": int(comprados or 0), "vendidos": int(vendidos or 0)}
            for sid, comprados, vendidos in (await self._session.execute(stmt)).all()
        }

    async def leads_by_store(self, store_ids: list[str], start: str, end: str) -> dict[str, int]:
        """Leads do mês (lançamento diário) — denominador da conversão."""
        if not store_ids:
            return {}
        stmt = (
            select(
                DailyIndicatorModel.store_id,
                func.coalesce(func.sum(DailyIndicatorModel.total_leads), 0),
            )
            .where(
                DailyIndicatorModel.store_id.in_(store_ids),
                DailyIndicatorModel.reference_date >= date.fromisoformat(start),
                DailyIndicatorModel.reference_date <= date.fromisoformat(end),
            )
            .group_by(DailyIndicatorModel.store_id)
        )
        return {str(sid): int(total or 0) for sid, total in (await self._session.execute(stmt)).all()}
