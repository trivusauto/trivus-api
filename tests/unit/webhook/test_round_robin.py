from src.modules.webhook.domain.round_robin import RoundRobin

r = RoundRobin()


def test_eligible() -> None:
    assert r.eligible([{"id": "a", "can_see_unassigned_leads": True}, {"id": "b", "can_see_unassigned_leads": False}]) == ["a"]


def test_pick_next() -> None:
    assert r.pick_next(["a", "b", "c"], "a") == "b"
    assert r.pick_next(["a", "b", "c"], "c") == "a"
    assert r.pick_next(["a", "b", "c"], None) == "a"
    assert r.pick_next([], "a") is None
