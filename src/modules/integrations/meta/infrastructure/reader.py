from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.marketing.infrastructure.orm import CampaignModel
from src.modules.stores.infrastructure.orm import StoreModel


@dataclass(frozen=True)
class MetaCampaignRow:
    store_id: str
    ad_account_id: str | None
    campaign_id: str
    meta_campaign_id: str


class MetaCampaignReader:
    """Campanhas com meta_campaign_id definido, já com o ad account (meta_ad_account_id)
    da loja — insumo do sync."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def campaigns_with_meta(self, store_id: str | None) -> list[MetaCampaignRow]:
        stmt = (
            select(CampaignModel.store_id, StoreModel.meta_ad_account_id,
                   CampaignModel.id, CampaignModel.meta_campaign_id)
            .join(StoreModel, StoreModel.id == CampaignModel.store_id)
            .where(CampaignModel.meta_campaign_id.isnot(None))
        )
        if store_id:
            stmt = stmt.where(CampaignModel.store_id == store_id)
        rows = (await self._session.execute(stmt)).all()
        return [
            MetaCampaignRow(
                store_id=str(row[0]),
                ad_account_id=str(row[1]) if row[1] is not None else None,
                campaign_id=str(row[2]),
                meta_campaign_id=str(row[3]),
            )
            for row in rows
        ]
