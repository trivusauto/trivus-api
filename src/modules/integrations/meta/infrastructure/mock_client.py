import hashlib
from datetime import date, timedelta

from src.modules.integrations.meta.domain.client import DailyInsight

_MIN_SPEND_CENTS = 5000        # piso de R$ 50,00/dia
_SPEND_SPREAD_CENTS = 20000    # variação de até R$ 200,00/dia


def _seed(meta_campaign_id: str, day: str) -> int:
    digest = hashlib.sha256(f"{meta_campaign_id}:{day}".encode()).hexdigest()
    return int(digest, 16)


class MockMetaClient:
    """Gasto sintético determinístico por (campanha, dia) — sem rede.

    É o default quando META_ENABLED=false: permite testar o fluxo ponta a ponta
    (sync -> campaign_daily_spend -> funil de custos) sem credenciais da Meta."""

    async def fetch_daily_insights(
        self,
        ad_account_id: str,
        meta_campaign_ids: list[str],
        since: str,
        until: str,
    ) -> list[DailyInsight]:
        start = date.fromisoformat(since)
        end = date.fromisoformat(until)
        insights: list[DailyInsight] = []
        day = start
        while day <= end:
            iso = day.isoformat()
            for meta_campaign_id in meta_campaign_ids:
                seed = _seed(meta_campaign_id, iso)
                spend = round((_MIN_SPEND_CENTS + seed % _SPEND_SPREAD_CENTS) / 100, 2)
                insights.append(DailyInsight(
                    meta_campaign_id=meta_campaign_id,
                    reference_date=iso,
                    spend=spend,
                    impressions=1000 + seed % 9000,
                    clicks=10 + seed % 200,
                ))
            day += timedelta(days=1)
        return insights
