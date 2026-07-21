from pydantic import BaseModel


class MetaSyncRequest(BaseModel):
    store_id: str | None = None    # None = todas as lojas com campanhas Meta
    since: str | None = None       # YYYY-MM-DD (default: janela padrão)
    until: str | None = None       # YYYY-MM-DD (default: hoje)
