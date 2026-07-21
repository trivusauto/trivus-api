import uuid
from datetime import date

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.integrations.meta.infrastructure.orm import CampaignDailySpendModel


class CampaignDailySpendRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, data: dict[str, object]) -> None:
        """Grava/atualiza o gasto de uma campanha num dia (chave: campaign_id + reference_date)."""
        values: dict[str, object] = {
            "id": str(uuid.uuid4()),
            "store_id": str(data["store_id"]),
            "campaign_id": str(data["campaign_id"]),
            "reference_date": date.fromisoformat(str(data["reference_date"])),
            "spend": data["spend"],
            "impressions": data.get("impressions"),
            "clicks": data.get("clicks"),
        }
        stmt = pg_insert(CampaignDailySpendModel).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["campaign_id", "reference_date"],
            set_={
                "store_id": values["store_id"],
                "spend": values["spend"],
                "impressions": values["impressions"],
                "clicks": values["clicks"],
            },
        )
        await self._session.execute(stmt)
