from dataclasses import dataclass


@dataclass
class Campaign:
    id: str
    store_id: str
    name: str
    started_at: str            # YYYY-MM-DD
    ended_at: str | None       # None = ativa
    budget: float | None
    link_code: str | None
