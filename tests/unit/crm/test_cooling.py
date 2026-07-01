from src.modules.crm.domain.cooling import Cooling


def test_active_rule_max_threshold() -> None:
    rules: list[dict[str, object]] = [{"hours_threshold": 24}, {"hours_threshold": 48}]
    result = Cooling().active_rule(50, rules)
    assert result is not None
    assert result["hours_threshold"] == 48


def test_active_rule_none_when_below() -> None:
    rules: list[dict[str, object]] = [{"hours_threshold": 24}, {"hours_threshold": 48}]
    assert Cooling().active_rule(10, rules) is None
