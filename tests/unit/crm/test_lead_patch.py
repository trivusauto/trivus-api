import re

from src.modules.crm.domain.lead_patch import LeadPatch

p = LeadPatch()


def test_agendamento_first_time() -> None:
    patch = p.agendamento({}, data_agendamento="2026-02-01", hora_agendamento="10:30", user_id="u1")
    assert patch["agendado_por"] == "u1"
    assert patch["hora_agendamento"] == "10:30:00"
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", str(patch["data_marcacao_agendamento"]))


def test_agendamento_cleared() -> None:
    patch = p.agendamento({"agendado_por": "u", "data_marcacao_agendamento": "2026-01-01"}, data_agendamento="", hora_agendamento="", user_id="u")
    assert patch["agendado_por"] is None and patch["data_marcacao_agendamento"] is None


def test_compareceu() -> None:
    patch = p.compareceu({}, True)
    assert patch["compareceu_agendamento"] is True
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", str(patch["data_compareceu"]))


def test_fechamento_money() -> None:
    patch = p.fechamento({}, receita="1.000,00", despesa="100,00", rentabilidade="900,00")
    assert patch["fechou_negocio"] is True
    assert patch["receita"] == 1000.0 and patch["despesa"] == 100.0 and patch["rentabilidade"] == 900.0
