from src.modules.crm.domain.stage_rules import StageRules

STAGES = [{"name": n} for n in ["RECEBIDOS", "CLASSIFICADOS", "QUALIFICADOS", "AGENDADOS", "EM ATENDIMENTO", "VEÍCULOS COMPRADOS", "VEÍCULOS VENDIDOS"]]
s = StageRules()


def test_normalize() -> None:
    assert s.normalize_stage_name("Veículos Vendidos") == "VEICULOS VENDIDOS"


def test_missing_to_advance() -> None:
    ok, missing = s.can_advance(STAGES, 0, 2, {"funil": "receptivo", "telefone": "11999999999"})
    assert ok is False
    assert sorted(m["field"] for m in missing) == ["ano", "cidade", "modelo", "nome"]


def test_allow_when_filled() -> None:
    assert s.can_advance(STAGES, 0, 1, {"funil": "r", "telefone": "1", "nome": "Ana", "cidade": "SP"})[0] is True


def test_em_atendimento_rules() -> None:
    base = {"funil": "r", "telefone": "1", "nome": "A", "cidade": "C", "modelo": "M", "ano": "2020", "data_agendamento": "2026-01-01", "hora_agendamento": "10:00"}
    assert s.can_advance(STAGES, 0, 4, {**base, "compareceu_agendamento": False})[0] is False
    assert s.can_advance(STAGES, 0, 4, {**base, "compareceu_agendamento": True, "vendedor_id": "v1"})[0] is True


def test_auto_stage_index() -> None:
    assert s.compute_auto_stage_index(STAGES, {"funil": "r", "telefone": "1", "nome": "A", "cidade": "C"}) == 1


def test_money_field_filled() -> None:
    assert s.is_field_filled({"receita": "1000"}, "receita") is True
    assert s.is_field_filled({"receita": ""}, "receita") is False
