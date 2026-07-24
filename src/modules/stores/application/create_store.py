from src.modules.stores.application.dto import CreateStoreInput
from src.modules.users.application.create_team_user import CreateTeamUserUseCase
from src.modules.users.application.dto import CreateTeamUserInput
from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.ports import StoreRepository


class CreateStoreUseCase:
    def __init__(self, stores: StoreRepository, team: CreateTeamUserUseCase | None = None) -> None:
        self._stores = stores
        self._team = team

    async def execute(self, data: CreateStoreInput) -> Store:
        payload: dict[str, object] = {"nome_fantasia": data.nome_fantasia, **data.fields}
        store = await self._stores.create(payload)

        # Gerentes criados na MESMA sessão: se um falhar, a loja também é desfeita
        # (o get_session só commita no fim do request).
        if data.managers and self._team is not None:
            for m in data.managers:
                await self._team.execute(CreateTeamUserInput(
                    email=m.email, password=m.password, name=m.name,
                    store_id=store.id, shop_role="gerente",
                ))
        return store
