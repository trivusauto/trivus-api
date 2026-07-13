from src.modules.marketing.domain.cost_funnel import build_cost_funnel
from src.modules.metrics.domain.metrics_core import traffic_light, unit_cost

Q = {"leads": 200, "classified": 160, "qualified": 112, "scheduled": 56, "attended": 40, "sales": 8}


def test_cpl_and_cac() -> None:
    f = build_cost_funnel(Q, investment=10000, revenue=125000)
    stages = {s["stage"]: s for s in f["stages"]}
    assert stages["leads"]["unit_cost"] == 50.0          # CPL = 10000/200
    assert stages["sales"]["unit_cost"] == 1250.0        # CAC = 10000/8


def test_conversion_rates() -> None:
    f = build_cost_funnel(Q, investment=10000, revenue=125000)
    stages = {s["stage"]: s for s in f["stages"]}
    assert stages["leads"]["conversion_from_previous"] is None
    assert stages["classified"]["conversion_from_previous"] == 80.0   # 160/200
    assert stages["qualified"]["conversion_from_previous"] == 70.0    # 112/160


def test_roas_roi() -> None:
    f = build_cost_funnel(Q, investment=10000, revenue=125000)
    assert f["roas"] == 12.5
    assert f["roi"] == 11.5


def test_zero_investment_safe() -> None:
    f = build_cost_funnel(Q, investment=0, revenue=125000)
    assert all(s["unit_cost"] is None for s in f["stages"])
    assert f["roas"] is None and f["roi"] is None


def test_zero_quantities_safe() -> None:
    f = build_cost_funnel({}, investment=1000, revenue=0)
    stages = {s["stage"]: s for s in f["stages"]}
    assert stages["leads"]["quantity"] == 0
    assert stages["classified"]["conversion_from_previous"] is None


def test_unit_cost_and_light() -> None:
    assert unit_cost(1000, 0) is None
    assert unit_cost(1000, 4) == 250.0
    assert unit_cost(None, 4) is None
    assert traffic_light(100, 100) == "green"
    assert traffic_light(85, 100) == "yellow"
    assert traffic_light(50, 100) == "red"
    assert traffic_light(50, 0) == "gray"
    assert traffic_light(50, None) == "gray"
