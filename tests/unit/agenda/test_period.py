from datetime import date
from src.modules.agenda.domain.period import AgendaPeriod

a = AgendaPeriod()
NOW = date(2026, 2, 15)


def test_date_field() -> None:
    assert a.date_field("agendamento") == "data_agendamento"
    assert a.date_field("comparecimento") == "data_compareceu"
    assert a.date_field("fechamento") == "data_fechou_negocio"


def test_ranges() -> None:
    assert a.resolve_range("today", now=NOW) == ("2026-02-15", "2026-02-15")
    assert a.resolve_range("month", now=NOW) == ("2026-02-01", "2026-02-28")
    assert a.resolve_range("from_today", now=NOW) == ("2026-02-15", None)


def test_custom_inverted() -> None:
    assert a.resolve_range("custom", "2026-02-20", "2026-02-10", now=NOW) == ("2026-02-10", "2026-02-20")
