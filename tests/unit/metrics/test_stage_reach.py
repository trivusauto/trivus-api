from src.modules.metrics.domain.stage_reach import StageReachContext


def test_passed_by_history() -> None:
    ctx = StageReachContext(stage_ids_at_or_after={"st3"}, leads_with_history={"l1"})
    assert ctx.passed({"id": "l1", "stage_id": "st0"}) is True


def test_passed_by_current_stage() -> None:
    ctx = StageReachContext(stage_ids_at_or_after={"st3", "st4"}, leads_with_history=set())
    assert ctx.passed({"id": "l2", "stage_id": "st4"}) is True
    assert ctx.passed({"id": "l3", "stage_id": "st0"}) is False
