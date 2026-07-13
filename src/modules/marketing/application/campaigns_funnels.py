from src.modules.marketing.application.marketing_funnel import MarketingFunnelUseCase
from src.modules.marketing.infrastructure.repository import CampaignRepository


class CampaignsFunnelsUseCase:
    """Um funil por campanha ativa/encerrada no período (Seções 2 e 3 da tela nova).
    A Seção 3 (comparação) usa este mesmo payload — o front plota leads/vendas/CAC/ROAS."""

    def __init__(self, funnel_uc: MarketingFunnelUseCase, campaigns: CampaignRepository) -> None:
        self._funnel_uc = funnel_uc
        self._campaigns = campaigns

    async def execute(self, store_id: str, start: str, end: str) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        for camp in await self._campaigns.list_in_period(store_id, start, end):
            funnel = await self._funnel_uc.execute([store_id], start, end, campaign_id=camp.id)
            out.append({"campaign": {"id": camp.id, "name": camp.name, "started_at": camp.started_at,
                                     "ended_at": camp.ended_at, "budget": camp.budget},
                        "funnel": funnel})
        return out
