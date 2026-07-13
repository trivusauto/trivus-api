import httpx


class InterestNotifier:
    """Notifica o comercial da holding via n8n (best-effort; nunca bloqueia o registro)."""

    def __init__(self, url: str | None) -> None:
        self._url = url

    async def notify(self, interest: dict[str, object]) -> None:
        if not self._url:
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(self._url, json=interest)
        except Exception:  # noqa: BLE001 — best-effort
            pass
