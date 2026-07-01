from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.agenda.application.list_agenda import ListAgendaUseCase
from src.modules.agenda.infrastructure.reader import AgendaReader
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.shared.infrastructure.database import get_session


def get_list_agenda_uc(session: AsyncSession = Depends(get_session)) -> ListAgendaUseCase:
    return ListAgendaUseCase(AgendaReader(session), SqlAlchemyUserRepository(session))
