import re
from datetime import date


def _today() -> str:
    return date.today().isoformat()


def parse_optional_money(s: str | None) -> float | None:
    if s is None or not any(ch.isdigit() for ch in str(s)):
        return None
    cleaned = re.sub(r"[^\d,]", "", str(s)).replace(",", ".")
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _has_digits(s: str | None) -> bool:
    return s is not None and any(ch.isdigit() for ch in str(s))


def _normalize_time(t: str | None) -> str | None:
    s = (t or "").strip()
    if re.match(r"^\d{2}:\d{2}$", s):
        return f"{s}:00"
    if re.match(r"^\d{2}:\d{2}:\d{2}", s):
        return s[:8]
    return None


class LeadPatch:
    def agendamento(self, prev: dict[str, object], data_agendamento: str | None, hora_agendamento: str | None, user_id: str | None) -> dict[str, object]:
        data_ag = (data_agendamento or "").strip() or None
        hora_ag = _normalize_time(hora_agendamento)
        had = bool(prev.get("data_agendamento") and prev.get("hora_agendamento"))
        will = bool(data_ag and hora_ag)
        agendado_por = prev.get("agendado_por")
        if will and not had and user_id:
            agendado_por = user_id
        if not will:
            agendado_por = None
        marcacao = prev.get("data_marcacao_agendamento")
        if will:
            if not had:
                marcacao = _today()
            elif not marcacao and data_ag:
                marcacao = data_ag[:10]
        else:
            marcacao = None
        return {"data_agendamento": data_ag, "hora_agendamento": hora_ag, "agendado_por": agendado_por, "data_marcacao_agendamento": marcacao}

    def compareceu(self, prev: dict[str, object], compareceu: bool) -> dict[str, object]:
        prev_comp = prev.get("compareceu_agendamento") is True
        data_comp: object = prev.get("data_compareceu")
        if compareceu is True and not prev_comp:
            data_comp = _today()
        if compareceu is not True:
            data_comp = None
        return {"compareceu_agendamento": compareceu, "data_compareceu": data_comp}

    def fechamento(self, prev: dict[str, object], receita: str | None, despesa: str | None, rentabilidade: str | None) -> dict[str, object]:
        prev_fechou = prev.get("fechou_negocio") is True
        data_f: object = prev.get("data_fechou_negocio") if prev_fechou else _today()
        has_rd = _has_digits(receita) or _has_digits(despesa)
        return {
            "fechou_negocio": True, "data_fechou_negocio": data_f,
            "rentabilidade": parse_optional_money(rentabilidade),
            "receita": parse_optional_money(receita) if has_rd else None,
            "despesa": parse_optional_money(despesa) if has_rd else None,
        }
