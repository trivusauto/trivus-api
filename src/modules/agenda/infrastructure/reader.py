from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.infrastructure.orm import UserModel
from src.modules.crm.infrastructure.orm import LeadModel
from src.modules.crm.infrastructure.repositories import lead_to_dict


class AgendaReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def query(
        self,
        *,
        store_id: str,
        apply_to: str,
        date_field: str,
        date_from: str,
        date_to: str | None,
        scope: dict[str, object],
        search: str | None,
        page: int,
        page_size: int,
        vendedor_id: str | None = None,
    ) -> tuple[list[dict[str, object]], int]:
        stmt = select(LeadModel).where(LeadModel.store_id == store_id)

        if vendedor_id:
            stmt = stmt.where(
                or_(LeadModel.vendedor_id == vendedor_id, LeadModel.agendado_por == vendedor_id)
            )

        if apply_to == "agendamento":
            stmt = stmt.where(LeadModel.data_agendamento.isnot(None), LeadModel.hora_agendamento.isnot(None))
        elif apply_to == "comparecimento":
            stmt = stmt.where(LeadModel.compareceu_agendamento.is_(True), LeadModel.data_compareceu.isnot(None))
        elif apply_to == "fechamento":
            stmt = stmt.where(LeadModel.fechou_negocio.is_(True), LeadModel.data_fechou_negocio.isnot(None))

        col = getattr(LeadModel, date_field)
        stmt = stmt.where(col >= date.fromisoformat(date_from))
        if date_to:
            stmt = stmt.where(col <= date.fromisoformat(date_to))

        if not scope.get("gestor"):
            uid = scope["user_id"]
            conds = [LeadModel.vendedor_id == uid, LeadModel.assigned_to == uid]
            if scope.get("include_unassigned"):
                conds.append(LeadModel.assigned_to.is_(None))
            stmt = stmt.where(or_(*conds))

        if search and search.strip():
            like = f"%{search.strip()}%"
            stmt = stmt.where(or_(
                LeadModel.nome.ilike(like),
                LeadModel.modelo.ilike(like),
                LeadModel.veiculo.ilike(like),
                LeadModel.telefone.ilike(like),
            ))

        total = int((await self._session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one())

        # Nome do vendedor via outer join com users — uma query, sem N+1.
        stmt = (
            stmt.add_columns(UserModel.name)
            .outerjoin(UserModel, UserModel.id == LeadModel.vendedor_id)
            .order_by(col)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows = (await self._session.execute(stmt)).all()
        return [{**lead_to_dict(lead), "vendedor_nome": nome} for lead, nome in rows], total
