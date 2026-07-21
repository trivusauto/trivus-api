from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DailyInsight:
    """Gasto diário de uma campanha na Meta (uma linha por campanha/dia)."""

    meta_campaign_id: str
    reference_date: str        # YYYY-MM-DD
    spend: float
    impressions: int | None
    clicks: int | None


class MetaAdsClient(Protocol):
    """Porta para a Marketing API da Meta. Duas implementações: mock e HTTP real
    (env-gated por META_ENABLED). O resto do sistema depende só desta interface."""

    async def fetch_daily_insights(
        self,
        ad_account_id: str,
        meta_campaign_ids: list[str],
        since: str,
        until: str,
    ) -> list[DailyInsight]: ...
