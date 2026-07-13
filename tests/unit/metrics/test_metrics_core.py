from src.modules.metrics.domain.metrics_core import (
    aggregate_by_origin_for_range, aggregate_totals_for_range, build_report_processed, normalize_funil_key,
)


def lead(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "created_at": "2026-02-10T12:00:00Z", "funil": "receptivo", "stage_id": None,
        "data_agendamento": None, "hora_agendamento": None, "data_marcacao_agendamento": None,
        "compareceu_agendamento": False, "data_compareceu": None,
        "fechou_negocio": False, "data_fechou_negocio": None, "rentabilidade": None,
    }
    base.update(over)
    return base


def test_normalize_funil() -> None:
    assert normalize_funil_key("prospeccao_ativa") == "prospeccao"
    assert normalize_funil_key("") == "receptivo"
    assert normalize_funil_key("xpto") == "outros"


def test_total_leads() -> None:
    assert aggregate_totals_for_range([lead()], "2026-02-01", "2026-02-28")["total_leads"] == 1


def test_scheduled_by_marcacao() -> None:
    t = aggregate_totals_for_range(
        [lead(data_agendamento="2026-02-20", hora_agendamento="10:00", data_marcacao_agendamento="2026-02-05")],
        "2026-02-01", "2026-02-10",
    )
    assert t["scheduled"] == 1


def test_conversions_and_revenue() -> None:
    t = aggregate_totals_for_range(
        [lead(fechou_negocio=True, data_fechou_negocio="2026-02-12", rentabilidade=1500)],
        "2026-02-01", "2026-02-28",
    )
    assert t["conversions"] == 1 and t["total_revenue"] == 1500


def test_by_origin() -> None:
    by = aggregate_by_origin_for_range([lead(funil="prospeccao_ativa")], "2026-02-01", "2026-02-28")
    assert by["prospeccao"]["total"] == 1 and by["receptivo"]["total"] == 0


def test_by_origin_classified() -> None:
    by = aggregate_by_origin_for_range([lead()], "2026-02-01", "2026-02-28",
                                       passed_qualificados=None, passed_classificados=lambda _lead: True)
    assert by["receptivo"]["classified"] == 1


def test_report_costs() -> None:
    leads = [lead(), lead(fechou_negocio=True, data_fechou_negocio="2026-02-12", rentabilidade=5000)]
    res = build_report_processed(leads, "2026-02-01", "2026-02-28",
                                 passed_qualificados=None, passed_classificados=lambda _lead: True,
                                 investment=1000)
    assert res["investment"] == 1000
    assert res["costs"]["cost_per_lead"] == 500.0        # 1000 / 2 leads receptivos
    assert res["costs"]["cac"] == 1000.0                 # 1000 / 1 venda
    assert res["summary"]["classified"] == 2
