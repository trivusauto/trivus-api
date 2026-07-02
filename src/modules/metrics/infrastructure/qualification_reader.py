from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.domain.stage_rules import StageRules
from src.modules.crm.infrastructure.orm import FunnelModel, StageHistoryModel, StageModel
from src.modules.metrics.domain.qualification import QualificationContext


class QualificationReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._rules = StageRules()

    async def build(self, store_ids: list[str]) -> QualificationContext:
        if not store_ids:
            return QualificationContext(set(), set())
        funnel_ids = list((await self._session.execute(
            select(FunnelModel.id).where(FunnelModel.store_id.in_(store_ids), FunnelModel.template_source_id.isnot(None))
        )).scalars().all())
        if not funnel_ids:
            return QualificationContext(set(), set())

        stages = list((await self._session.execute(
            select(StageModel).where(StageModel.funnel_id.in_(funnel_ids)).order_by(StageModel.sort_order)
        )).scalars().all())

        by_funnel: dict[str, list[StageModel]] = defaultdict(list)
        for s in stages:
            by_funnel[str(s.funnel_id)].append(s)

        at_or_after: set[str] = set()
        qualificados_ids: set[str] = set()
        for fstages in by_funnel.values():
            fstages.sort(key=lambda s: s.sort_order or 0)
            qi = next(
                (i for i, s in enumerate(fstages) if self._rules.normalize_stage_name(s.name) == "QUALIFICADOS"), -1
            )
            if qi < 0:
                continue
            qualificados_ids.add(str(fstages[qi].id))
            for s in fstages[qi:]:
                at_or_after.add(str(s.id))

        leads_with_history: set[str] = set()
        if qualificados_ids:
            rows = (await self._session.execute(
                select(StageHistoryModel.lead_id).where(StageHistoryModel.stage_id.in_(qualificados_ids))
            )).scalars().all()
            leads_with_history = {str(r) for r in rows}

        return QualificationContext(at_or_after, leads_with_history)
