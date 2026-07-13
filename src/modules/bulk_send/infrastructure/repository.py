import uuid
from datetime import datetime, timezone

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.bulk_send.infrastructure.orm import BulkSendContactModel, BulkSendModel
from src.shared.domain.errors import NotFoundError


class BulkSendRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, object]) -> str:
        row = BulkSendModel(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return str(row.id)

    async def list(self) -> list[dict[str, object]]:
        rows = (await self._session.execute(
            select(BulkSendModel).order_by(BulkSendModel.created_at.desc())
        )).scalars().all()
        return [{"id": str(r.id), "title": r.title, "total_contacts": r.total_contacts, "status": r.status,
                 "success_count": r.success_count, "error_count": r.error_count} for r in rows]


class BulkSendContactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, rows: list[dict[str, object]]) -> None:
        for r in rows:
            self._session.add(BulkSendContactModel(id=str(uuid.uuid4()), **r))
        await self._session.flush()

    async def list_ordered(self, bulk_send_id: str) -> list[dict[str, object]]:
        rank = case((BulkSendContactModel.status == "pending", 0),
                    (BulkSendContactModel.status == "sent", 1), else_=2)
        rows = (await self._session.execute(
            select(BulkSendContactModel)
            .where(BulkSendContactModel.bulk_send_id == bulk_send_id)
            .order_by(rank)
        )).scalars().all()
        return [{"id": str(r.id), "phone": r.phone, "status": r.status,
                 "error_message": r.error_message} for r in rows]

    async def update_status(self, contact_id: str, status: str, error_message: str | None) -> None:
        row = await self._session.get(BulkSendContactModel, contact_id)
        if row is None:
            raise NotFoundError("Contato não encontrado")
        row.status = status
        row.error_message = error_message
        row.sent_at = datetime.now(timezone.utc) if status == "sent" else None
        await self._session.flush()
