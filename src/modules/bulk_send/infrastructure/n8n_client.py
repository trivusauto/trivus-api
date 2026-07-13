import httpx


class N8nClient:
    """Dispara o fluxo n8n a partir do servidor (spec §8.2).
    Sem URL configurada: salva no banco mas não chama — comportamento do sistema atual."""

    def __init__(self, url: str | None) -> None:
        self._url = url

    async def dispatch(self, send_id: str, data: dict[str, object]) -> None:
        if not self._url:
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(self._url, json={"bulk_send_id": send_id, "title": data.get("title")})
        except Exception:  # noqa: BLE001 — não bloqueia a criação do disparo
            pass
