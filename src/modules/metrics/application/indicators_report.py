from typing import Protocol


class IndicatorListRepo(Protocol):
    async def list(self, store_id: str, date_from: str, date_to: str) -> list[dict[str, object]]: ...


class GoalListRepo(Protocol):
    async def list(self, store_id: str, year: int, month: int) -> list[dict[str, object]]: ...


class IndicatorsReportUseCase:
    def __init__(self, indicators_repo: IndicatorListRepo, goals_repo: GoalListRepo) -> None:
        self._indicators = indicators_repo
        self._goals = goals_repo

    async def execute(self, store_id: str, date_from: str, date_to: str, year: int, month: int) -> dict[str, object]:
        from src.modules.metrics.domain.indicators_report import build_indicators_report
        indicators = await self._indicators.list(store_id, date_from, date_to)
        goals = await self._goals.list(store_id, year, month)
        return build_indicators_report(indicators, goals)
