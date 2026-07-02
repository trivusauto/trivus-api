from src.modules.indicators.infrastructure.repository import IndicatorRepository


class ListIndicatorsUseCase:
    def __init__(self, repo: IndicatorRepository) -> None:
        self._repo = repo

    async def execute(self, store_id: str, date_from: str | None, date_to: str | None) -> list[dict[str, object]]:
        return await self._repo.list(store_id, date_from, date_to)


class UpsertIndicatorUseCase:
    def __init__(self, repo: IndicatorRepository) -> None:
        self._repo = repo

    async def execute(self, data: dict[str, object]) -> None:
        await self._repo.upsert(data)
