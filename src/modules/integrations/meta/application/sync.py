from collections import defaultdict
from datetime import date, timedelta

from src.modules.integrations.meta.domain.client import MetaAdsClient
from src.modules.integrations.meta.infrastructure.reader import MetaCampaignReader, MetaCampaignRow
from src.modules.integrations.meta.infrastructure.repository import CampaignDailySpendRepository

_DEFAULT_LOOKBACK_DAYS = 7


class SyncMetaSpendUseCase:
    """Sincroniza o gasto diário das campanhas com meta_campaign_id definido.

    Agrupa por loja (cada loja = um ad account), chama o client (mock ou HTTP,
    conforme META_ENABLED) e faz upsert em campaign_daily_spend. Sem período no
    body, usa os últimos dias (janela padrão)."""

    def __init__(self, reader: MetaCampaignReader, repo: CampaignDailySpendRepository,
                 client: MetaAdsClient) -> None:
        self._reader = reader
        self._repo = repo
        self._client = client

    async def execute(self, store_id: str | None = None, since: str | None = None,
                      until: str | None = None) -> dict[str, object]:
        until_date = date.fromisoformat(until) if until else date.today()
        since_date = (date.fromisoformat(since) if since
                      else until_date - timedelta(days=_DEFAULT_LOOKBACK_DAYS))

        rows = await self._reader.campaigns_with_meta(store_id)
        by_store: dict[str, list[MetaCampaignRow]] = defaultdict(list)
        for row in rows:
            by_store[row.store_id].append(row)

        written = 0
        skipped_no_account = 0
        for sid, campaigns in by_store.items():
            ad_account_id = campaigns[0].ad_account_id
            if not ad_account_id:
                skipped_no_account += len(campaigns)
                continue
            campaign_by_meta = {c.meta_campaign_id: c.campaign_id for c in campaigns}
            insights = await self._client.fetch_daily_insights(
                ad_account_id, list(campaign_by_meta.keys()),
                since_date.isoformat(), until_date.isoformat())
            for insight in insights:
                campaign_id = campaign_by_meta.get(insight.meta_campaign_id)
                if campaign_id is None:
                    continue
                await self._repo.upsert({
                    "store_id": sid,
                    "campaign_id": campaign_id,
                    "reference_date": insight.reference_date,
                    "spend": insight.spend,
                    "impressions": insight.impressions,
                    "clicks": insight.clicks,
                })
                written += 1

        return {
            "rows_written": written,
            "campaigns_synced": len(rows),
            "skipped_no_ad_account": skipped_no_account,
            "since": since_date.isoformat(),
            "until": until_date.isoformat(),
        }
