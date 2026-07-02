from src.modules.metrics.domain.indicators_report import build_indicators_report


def ind(**o: object) -> dict[str, object]:
    base: dict[str, object] = {
        "origin": "receptivo", "total_leads": 0, "qualified_leads": 0, "scheduled_leads": 0,
        "attended_leads": 0, "converted_leads": 0, "profitability": 0, "daily_expenses": 0,
    }
    base.update(o)
    return base


def test_net_revenue_and_receptivo_only_total() -> None:
    indicators = [
        ind(origin="receptivo", total_leads=10, qualified_leads=6, converted_leads=2, profitability=1000, daily_expenses=200),
        ind(origin="prospeccao", total_leads=99, converted_leads=1, profitability=500, daily_expenses=100),
    ]
    res = build_indicators_report(indicators, [])
    assert res["summary"]["totalLeads"] == 10
    assert res["summary"]["qualified"] == 6
    assert res["summary"]["converted"] == 3
    assert res["summary"]["revenue"] == 800 + 400


def test_goals_comparison() -> None:
    indicators = [ind(origin="receptivo", converted_leads=2, profitability=1000, daily_expenses=0)]
    goals = [{"origin": "receptivo", "conversions_quantity": 5, "profitability_goal": 3000}]
    res = build_indicators_report(indicators, goals)
    gc = res["goalsComparison"][0]
    assert gc["origin"] == "Receptivo"
    assert gc["Meta Conversões"] == 5 and gc["Real Conversões"] == 2
    assert gc["Meta Receita"] == 3000 and gc["Real Receita"] == 1000
