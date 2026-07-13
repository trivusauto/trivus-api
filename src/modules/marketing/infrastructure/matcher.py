from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.marketing.domain.campaign_match import match_campaign_by_link
from src.modules.marketing.infrastructure.repository import CampaignRepository


class CampaignMatcher:
    """Adapter usado pelo webhook: tenta identificar a campanha do lead receptivo
    pelo link_code das campanhas ativas da loja."""

    def __init__(self, session: AsyncSession) -> None:
        self._campaigns = CampaignRepository(session)

    async def match(self, store_id: str, body: dict[str, object]) -> str | None:
        camps = await self._campaigns.active_with_link_code(store_id)
        return match_campaign_by_link([{"id": c.id, "link_code": c.link_code} for c in camps], body)
