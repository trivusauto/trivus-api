from src.modules.agenda.domain.period import AgendaPeriod
from src.modules.agenda.infrastructure.reader import AgendaReader
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.shared.interface.auth_deps import CurrentUser


class ListAgendaUseCase:
    def __init__(self, reader: AgendaReader, users: SqlAlchemyUserRepository) -> None:
        self._reader = reader
        self._users = users
        self._period = AgendaPeriod()

    async def execute(self, current: CurrentUser, query: dict[str, object]) -> dict[str, object]:
        gestor = current.role in ("client", "admin")
        include_unassigned = False
        if current.role == "shop_user":
            u = await self._users.get_by_id(current.user_id)
            gestor = bool(u and u.shop_role == "gerente")
            include_unassigned = bool(u and u.can_see_unassigned_leads)

        apply_to = str(query.get("apply_to") or "agendamento")
        date_field = self._period.date_field(apply_to)
        date_from, date_to = self._period.resolve_range(
            str(query.get("preset") or "month"),
            str(query.get("from") or ""),
            str(query.get("to") or ""),
        )

        page = int(str(query.get("page") or 1))
        raw_size = int(str(query.get("page_size") or 25))
        page_size = raw_size if raw_size in (25, 50, 100) else 25

        items, total = await self._reader.query(
            store_id=str(query["store_id"]),
            apply_to=apply_to,
            date_field=date_field,
            date_from=date_from,
            date_to=date_to,
            scope={"gestor": gestor, "user_id": current.user_id, "include_unassigned": include_unassigned},
            search=str(query["search"]) if query.get("search") else None,
            page=page,
            page_size=page_size,
        )
        return {"items": items, "total": total, "page": page, "page_size": page_size}
