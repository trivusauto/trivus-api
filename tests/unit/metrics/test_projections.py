import pytest

from src.modules.metrics.application.projections import ProjectionsUseCase


class FakeReader:
    async def leads_for_stores(self, ids: list[str]) -> list[dict[str, object]]:
        return [{"id": "l1", "created_at": "2026-07-05T12:00:00Z", "funil": "receptivo", "stage_id": None,
                 "data_agendamento": None, "hora_agendamento": None, "data_marcacao_agendamento": None,
                 "compareceu_agendamento": False, "data_compareceu": None,
                 "fechou_negocio": True, "data_fechou_negocio": "2026-07-05", "rentabilidade": 1000}]


class FakeWorkdays:
    def working_days_in_month(self, y: int, m: int) -> int:
        return 26

    def remaining_working_days(self, y: int, m: int, d: int) -> int:
        return 13


class _Ctx:
    @staticmethod
    def passed(lead: dict[str, object]) -> bool:
        return False


class FakeReach:
    async def build(self, ids: list[str], stage: str) -> _Ctx:
        return _Ctx()


class FakeGoals:
    async def list(self, store_id: str, year: int, month: int) -> list[dict[str, object]]:
        return [{"origin": "receptivo", "leads_quantity": 10, "qualified_quantity": 0,
                 "scheduled_quantity": 0, "attended_quantity": 0, "conversions_quantity": 2,
                 "profitability_goal": 5000, "marketing_investment_goal": 0}]


@pytest.mark.asyncio
async def test_projection_trio_and_light() -> None:
    uc = ProjectionsUseCase(FakeReader(), FakeWorkdays(), FakeReach(), FakeGoals())
    res = await uc.execute(["s1"], 2026, 7)
    conv = next(m for m in res["metrics"] if m["key"] == "conversions")
    assert conv["goal"] == 2 and conv["actual"] == 1
    assert conv["projected"] == 2.0            # 1 + (1/13)*13
    assert conv["light"] == "green"            # projetando bater a meta
    assert res["working_days"] == {"total": 26, "elapsed": 13, "remaining": 13}


@pytest.mark.asyncio
async def test_projection_without_goals_gray() -> None:
    class NoGoals:
        async def list(self, store_id: str, year: int, month: int) -> list[dict[str, object]]:
            return []

    uc = ProjectionsUseCase(FakeReader(), FakeWorkdays(), FakeReach(), NoGoals())
    res = await uc.execute(["s1"], 2026, 7)
    assert all(m["light"] == "gray" for m in res["metrics"])
