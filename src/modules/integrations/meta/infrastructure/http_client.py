import json

import httpx

from src.modules.integrations.meta.domain.client import DailyInsight

_DEFAULT_API_VERSION = "v21.0"
_TIMEOUT_SECONDS = 30


class HttpMetaClient:
    """Cliente real da Marketing API da Meta (Graph API).

    Usado quando META_ENABLED=true. O token vai no header Authorization (nunca na
    URL). A chamada de rede é simples e não é coberta por teste — o contrato
    testado é a interface MetaAdsClient (ver MockMetaClient)."""

    def __init__(self, access_token: str, api_version: str = _DEFAULT_API_VERSION) -> None:
        self._token = access_token
        self._base_url = f"https://graph.facebook.com/{api_version}"

    async def fetch_daily_insights(
        self,
        ad_account_id: str,
        meta_campaign_ids: list[str],
        since: str,
        until: str,
    ) -> list[DailyInsight]:
        params: dict[str, str] = {
            "level": "campaign",
            "time_increment": "1",
            "fields": "campaign_id,spend,impressions,clicks",
            "time_range": json.dumps({"since": since, "until": until}),
        }
        wanted = set(meta_campaign_ids)
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.get(
                f"{self._base_url}/{ad_account_id}/insights",
                params=params,
                headers={"Authorization": f"Bearer {self._token}"},
            )
            resp.raise_for_status()
            rows = resp.json().get("data", [])

        insights: list[DailyInsight] = []
        for row in rows:
            meta_campaign_id = str(row.get("campaign_id"))
            if wanted and meta_campaign_id not in wanted:
                continue
            insights.append(DailyInsight(
                meta_campaign_id=meta_campaign_id,
                reference_date=str(row.get("date_start")),
                spend=float(row.get("spend") or 0),
                impressions=int(row["impressions"]) if row.get("impressions") is not None else None,
                clicks=int(row["clicks"]) if row.get("clicks") is not None else None,
            ))
        return insights
