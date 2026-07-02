from src.modules.metrics.domain.team import build_team_performance


def lead(**o: object) -> dict[str, object]:
    base: dict[str, object] = {
        "created_at": "2026-02-10T12:00:00Z", "assigned_to": None, "vendedor_id": None, "agendado_por": None,
        "data_agendamento": None, "hora_agendamento": None, "data_marcacao_agendamento": None,
        "compareceu_agendamento": False, "data_compareceu": None,
        "fechou_negocio": False, "data_fechou_negocio": None, "rentabilidade": None,
    }
    base.update(o)
    return base


def test_conversion_to_vendedor() -> None:
    res = build_team_performance(
        [lead(fechou_negocio=True, data_fechou_negocio="2026-02-12", rentabilidade=1000, vendedor_id="v1")],
        [{"id": "v1", "name": "Vend 1", "shop_role": "vendedor"}],
        "2026-02-01", "2026-02-28",
    )
    row = next(r for r in res["rows"] if r["user_id"] == "v1")
    assert row["converted"] == 1 and row["revenue"] == 1000
