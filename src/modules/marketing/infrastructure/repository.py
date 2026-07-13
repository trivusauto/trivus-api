import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.marketing.domain.entities import Campaign
from src.modules.marketing.infrastructure.orm import CampaignModel
from src.shared.domain.errors import NotFoundError


def _to_domain(r: CampaignModel) -> Campaign:
    return Campaign(id=str(r.id), store_id=str(r.store_id), name=r.name,
                    started_at=r.started_at.isoformat(),
                    ended_at=r.ended_at.isoformat() if r.ended_at else None,
                    budget=float(r.budget) if r.budget is not None else None,
                    link_code=r.link_code)


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_store(self, store_id: str) -> list[Campaign]:
        rows = (await self._session.execute(
            select(CampaignModel).where(CampaignModel.store_id == store_id)
            .order_by(CampaignModel.started_at.desc())
        )).scalars().all()
        return [_to_domain(r) for r in rows]

    async def list_in_period(self, store_id: str, start: str, end: str) -> list[Campaign]:
        """Ativas ou encerradas dentro do período (spec: 'ativa ou encerrada no período')."""
        rows = (await self._session.execute(
            select(CampaignModel).where(
                CampaignModel.store_id == store_id,
                CampaignModel.started_at <= date.fromisoformat(end),
                or_(CampaignModel.ended_at.is_(None), CampaignModel.ended_at >= date.fromisoformat(start)),
            ).order_by(CampaignModel.started_at.desc())
        )).scalars().all()
        return [_to_domain(r) for r in rows]

    async def get(self, campaign_id: str) -> Campaign | None:
        r = await self._session.get(CampaignModel, campaign_id)
        return _to_domain(r) if r else None

    async def create(self, data: dict[str, object]) -> Campaign:
        row = CampaignModel(
            id=str(uuid.uuid4()),
            store_id=str(data["store_id"]), name=str(data["name"]),
            link_code=data.get("link_code"),
            started_at=date.fromisoformat(str(data["started_at"])),
            ended_at=date.fromisoformat(str(data["ended_at"])) if data.get("ended_at") else None,
            budget=data.get("budget"),
        )
        self._session.add(row)
        await self._session.flush()
        return _to_domain(row)

    async def update(self, campaign_id: str, data: dict[str, object]) -> Campaign:
        row = await self._session.get(CampaignModel, campaign_id)
        if row is None:
            raise NotFoundError("Campanha não encontrada")
        if data.get("name") is not None:
            row.name = str(data["name"])
        if "link_code" in data:
            row.link_code = str(data["link_code"]) if data["link_code"] is not None else None
        if "budget" in data:
            row.budget = data["budget"]  # type: ignore[assignment]
        if data.get("started_at"):
            row.started_at = date.fromisoformat(str(data["started_at"]))
        if "ended_at" in data:
            row.ended_at = date.fromisoformat(str(data["ended_at"])) if data["ended_at"] else None
        await self._session.flush()
        return _to_domain(row)

    async def active_with_link_code(self, store_id: str) -> list[Campaign]:
        rows = (await self._session.execute(
            select(CampaignModel).where(CampaignModel.store_id == store_id,
                                        CampaignModel.link_code.isnot(None),
                                        CampaignModel.ended_at.is_(None))
        )).scalars().all()
        return [_to_domain(r) for r in rows]
