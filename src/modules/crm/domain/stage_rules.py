import unicodedata

_MONEY = {"valor_tabela_fipe", "saldo_quitacao", "valor_pretendido", "valor_compra", "receita", "despesa", "rentabilidade"}
_SELECT_BOOL = {"tem_financiamento", "compareceu_agendamento"}

STAGE_FIELD_RULES: dict[str, dict[str, object]] = {
    "RECEBIDOS": {"required": ["funil", "telefone"], "labels": {"funil": "Funil", "telefone": "Telefone"}},
    "CLASSIFICADOS": {"required": ["nome", "cidade"], "labels": {"nome": "Nome", "cidade": "Cidade"}},
    "QUALIFICADOS": {"required": ["modelo", "ano"], "labels": {"modelo": "Modelo do veículo", "ano": "Ano"}},
    "AGENDADOS": {"required": ["data_agendamento", "hora_agendamento"], "labels": {"data_agendamento": "Data", "hora_agendamento": "Horário"}},
    "EM ATENDIMENTO": {"required": ["compareceu_agendamento", "vendedor_id"], "labels": {"compareceu_agendamento": "Compareceu?", "vendedor_id": "Vendedor"}},
    "VEICULOS COMPRADOS": {"required": ["valor_compra"], "labels": {"valor_compra": "Valor de compra"}},
    "VEICULOS VENDIDOS": {"required": ["receita", "despesa", "rentabilidade"], "labels": {"receita": "Valor venda", "despesa": "Despesa", "rentabilidade": "Rentabilidade"}},
}


class StageRules:
    def normalize_stage_name(self, name: str | None) -> str:
        n = unicodedata.normalize("NFD", name or "")
        n = "".join(c for c in n if unicodedata.category(c) != "Mn")
        return n.upper().strip()

    def rules_for(self, stage_name: str | None) -> dict[str, object] | None:
        return STAGE_FIELD_RULES.get(self.normalize_stage_name(stage_name))

    def is_em_atendimento(self, stage_name: str | None) -> bool:
        return self.normalize_stage_name(stage_name) == "EM ATENDIMENTO"

    def is_field_filled(self, lead: dict[str, object], key: str) -> bool:
        v = lead.get(key)
        if key in _MONEY:
            if v is None or v == "":
                return False
            if isinstance(v, (int, float)):
                return True
            return any(ch.isdigit() for ch in str(v))
        if key in _SELECT_BOOL:
            return v is True or v is False
        if key == "telefone":
            return any(ch.isdigit() for ch in str(v or ""))
        if key in ("funil", "hora_agendamento"):
            return v is not None and str(v).strip() != ""
        if isinstance(v, str):
            return v.strip() != ""
        return v is not None and v != ""

    def _missing_for_stage(self, lead: dict[str, object], rules: dict[str, object], stage_name: str | None) -> list[dict[str, object]]:
        labels = rules["labels"]
        assert isinstance(labels, dict)
        required = rules["required"]
        assert isinstance(required, list)
        if self.is_em_atendimento(stage_name):
            if lead.get("compareceu_agendamento") is not True:
                return [{"field": "compareceu_agendamento", "label": labels["compareceu_agendamento"]}]
            if not self.is_field_filled(lead, "vendedor_id"):
                return [{"field": "vendedor_id", "label": labels["vendedor_id"]}]
            return []
        return [{"field": k, "label": labels.get(k, k)} for k in required if not self.is_field_filled(lead, k)]

    def can_advance(self, stages: list[dict[str, object]], from_index: int, to_index: int, lead: dict[str, object]) -> tuple[bool, list[dict[str, object]]]:
        missing: list[dict[str, object]] = []
        if not stages or to_index <= from_index:
            return True, missing
        for i in range(from_index, to_index + 1):
            rules = self.rules_for(str(stages[i].get("name", "")))
            if not rules:
                continue
            for item in self._missing_for_stage(lead, rules, str(stages[i].get("name", ""))):
                missing.append({"stage_name": stages[i].get("name"), **item})
        return len(missing) == 0, missing

    def compute_auto_stage_index(self, stages: list[dict[str, object]], lead: dict[str, object]) -> int:
        if not stages:
            return 0
        max_index = 0
        for i, stage in enumerate(stages):
            rules = self.rules_for(str(stage.get("name", "")))
            if not rules:
                if i == 0:
                    max_index = 0
                continue
            if not self._missing_for_stage(lead, rules, str(stage.get("name", ""))):
                max_index = i
            elif i > 0:
                break
        return max_index
