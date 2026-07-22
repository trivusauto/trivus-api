from src.modules.auth.domain.ports import UserRepository
from src.modules.crm.infrastructure.repositories import LeadRepository


class CreateLeadUseCase:
    def __init__(self, leads: LeadRepository) -> None:
        self._leads = leads

    async def execute(self, data: dict[str, object]) -> dict[str, object]:
        return await self._leads.create(data)


class UpdateLeadUseCase:
    def __init__(self, leads: LeadRepository) -> None:
        self._leads = leads

    async def execute(self, lead_id: str, data: dict[str, object]) -> dict[str, object]:
        return await self._leads.update(lead_id, data)


class ListLeadsUseCase:
    def __init__(self, leads: LeadRepository, users: UserRepository | None = None) -> None:
        self._leads = leads
        self._users = users

    async def execute(
        self, store_id: str, user: object, assigned_to: str | None = None
    ) -> list[dict[str, object]]:
        """Resolve a visibilidade do quadro por papel (espelha o legado) e aplica
        o filtro opcional por responsável.

        - admin / client (dono) → veem o funil inteiro da loja.
        - shop_user gerente → vê tudo.
        - shop_user com ``can_see_unassigned_leads`` → próprios + não atribuídos.
        - demais shop_users (sdr, vendedor) → só os próprios.
        """
        restrict_to_user: str | None = None
        include_unassigned = False
        if getattr(user, "role", None) == "shop_user":
            uid = getattr(user, "user_id", None)
            u = await self._users.get_by_id(uid) if (self._users and uid) else None
            is_manager = bool(u and getattr(u, "shop_role", None) == "gerente")
            if not is_manager:
                restrict_to_user = uid
                include_unassigned = bool(u and getattr(u, "can_see_unassigned_leads", False))
        return await self._leads.list_for_board(
            store_id,
            restrict_to_user=restrict_to_user,
            include_unassigned=include_unassigned,
            assigned_to=assigned_to,
        )


class DeleteLeadUseCase:
    def __init__(self, leads: LeadRepository) -> None:
        self._leads = leads

    async def execute(self, lead_id: str) -> None:
        await self._leads.delete(lead_id)
