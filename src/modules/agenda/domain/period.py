import calendar
from datetime import date, timedelta

_FIELD = {"agendamento": "data_agendamento", "comparecimento": "data_compareceu", "fechamento": "data_fechou_negocio"}


def _eom(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


class AgendaPeriod:
    def date_field(self, apply_to: str) -> str:
        return _FIELD.get(apply_to, _FIELD["agendamento"])

    def resolve_range(self, preset: str, custom_from: str = "", custom_to: str = "", now: date | None = None) -> tuple[str, str | None]:
        now = now or date.today()
        today = now.isoformat()
        if preset == "from_today":
            return today, None
        if preset == "today":
            return today, today
        if preset == "yesterday":
            y = (now - timedelta(days=1)).isoformat()
            return y, y
        if preset == "previous_month":
            first_prev = date(now.year, now.month, 1) - timedelta(days=1)
            return date(first_prev.year, first_prev.month, 1).isoformat(), _eom(first_prev).isoformat()
        if preset == "custom" and custom_from and custom_to:
            return (custom_to, custom_from) if custom_from > custom_to else (custom_from, custom_to)
        return date(now.year, now.month, 1).isoformat(), _eom(now).isoformat()
