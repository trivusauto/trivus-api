import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.infrastructure.orm import UserModel
from src.modules.crm.infrastructure.orm import LeadModel
from src.modules.stores.infrastructure.orm import StoreModel


class WebhookStoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_webhook_token(self, token: str) -> StoreModel | None:
        return (await self._session.execute(select(StoreModel).where(StoreModel.webhook_token == token))).scalar_one_or_none()

    async def update_last_sdr(self, store_id: str, sdr_id: str | None) -> None:
        row = await self._session.get(StoreModel, store_id)
        if row is not None:
            row.last_assigned_sdr_id = sdr_id
            await self._session.flush()


class WebhookLeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_duplicate(self, store_id: str, lid: str | None, phone_variants: list[str]) -> LeadModel | None:
        conds = []
        if lid:
            conds.append(LeadModel.lid == lid)
            conds.append(LeadModel.telefone == lid)
        for v in phone_variants:
            conds.append(LeadModel.telefone == v)
        if not conds:
            return None
        stmt = select(LeadModel).where(LeadModel.store_id == store_id, or_(*conds)).order_by(LeadModel.created_at).limit(1)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def enrich(self, lead: LeadModel, lid: str | None, phone: str | None) -> None:
        changed = False
        if lid and not lead.lid:
            lead.lid = lid
            changed = True
        existing_digits = "".join(ch for ch in (lead.telefone or "") if ch.isdigit())
        if phone and (not existing_digits or len(existing_digits) > 11):
            lead.telefone = phone
            changed = True
        if changed:
            await self._session.flush()

    async def create(self, data: dict[str, object]) -> LeadModel:
        row = LeadModel(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return row


class WebhookUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_sdrs(self, store_id: str) -> list[dict[str, object]]:
        stmt = select(UserModel).where(
            UserModel.parent_store_id == store_id,
            UserModel.role == "shop_user",
            UserModel.shop_role == "sdr",
            UserModel.active.is_(True),
        ).order_by(UserModel.name)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [{"id": str(r.id), "can_see_unassigned_leads": r.can_see_unassigned_leads} for r in rows]
