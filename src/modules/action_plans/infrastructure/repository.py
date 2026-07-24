import uuid
from datetime import date, datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.action_plans.infrastructure.orm import ActionPlanModel, ActionPlanStepModel
from src.modules.auth.infrastructure.orm import UserModel


def _coerce_dates(data: dict[str, object]) -> dict[str, object]:
    """Aceita `due_date` como string ISO (o que o front manda) e converte para date."""
    out = dict(data)
    v = out.get("due_date")
    if isinstance(v, str) and v:
        out["due_date"] = date.fromisoformat(v)
    elif v == "":
        out["due_date"] = None
    return out


def _ids(plan: dict[str, object]) -> list[object]:
    value = plan.get("responsible_ids")
    return list(value) if isinstance(value, list) else []


def _step_to_dict(r: ActionPlanStepModel) -> dict[str, object]:
    return {
        "id": str(r.id),
        "plan_id": str(r.plan_id),
        "title": r.title,
        "description": r.description,
        "due_date": r.due_date.isoformat() if r.due_date else None,
        "done": r.done,
        "sort_order": r.sort_order,
    }


def _plan_to_dict(r: ActionPlanModel) -> dict[str, object]:
    return {
        "id": str(r.id),
        "store_id": str(r.store_id),
        "title": r.title,
        "description": r.description,
        "status": r.status,
        "due_date": r.due_date.isoformat() if r.due_date else None,
        "responsible_ids": list(r.responsible_ids or []),
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


class ActionPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_store(self, store_id: str) -> list[dict[str, object]]:
        rows = (await self._session.execute(
            select(ActionPlanModel)
            .where(ActionPlanModel.store_id == store_id)
            .order_by(ActionPlanModel.created_at.desc())
        )).scalars().all()
        plans = [_plan_to_dict(r) for r in rows]
        if not plans:
            return plans

        plan_ids = [str(p["id"]) for p in plans]

        # Steps de todos os planos numa query, agrupados em memória — sem N+1.
        step_rows = (await self._session.execute(
            select(ActionPlanStepModel)
            .where(ActionPlanStepModel.plan_id.in_(plan_ids))
            .order_by(ActionPlanStepModel.sort_order, ActionPlanStepModel.title)
        )).scalars().all()
        steps_by_plan: dict[str, list[dict[str, object]]] = {}
        for s in step_rows:
            steps_by_plan.setdefault(str(s.plan_id), []).append(_step_to_dict(s))

        # Nomes dos responsáveis (join users) — uma query para todos os ids.
        all_ids = {str(rid) for p in plans for rid in _ids(p)}
        names: dict[str, str] = {}
        if all_ids:
            urows = (await self._session.execute(
                select(UserModel.id, UserModel.name).where(UserModel.id.in_(all_ids))
            )).all()
            names = {str(uid): (name or "") for uid, name in urows}

        for p in plans:
            p["responsible_names"] = [names.get(str(rid), "") for rid in _ids(p)]
            p["steps"] = steps_by_plan.get(str(p["id"]), [])
        return plans

    async def create(self, data: dict[str, object]) -> dict[str, object]:
        row = ActionPlanModel(id=str(uuid.uuid4()), **_coerce_dates(data))
        self._session.add(row)
        await self._session.flush()
        return _plan_to_dict(row)

    async def update(self, plan_id: str, data: dict[str, object]) -> dict[str, object]:
        row = await self._session.get(ActionPlanModel, plan_id)
        if row is None:
            raise ValueError(f"ActionPlan {plan_id} not found")
        for k, v in _coerce_dates(data).items():
            setattr(row, k, v)
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return _plan_to_dict(row)

    async def delete(self, plan_id: str) -> None:
        await self._session.execute(delete(ActionPlanModel).where(ActionPlanModel.id == plan_id))

    # ── Steps ──────────────────────────────────────────────────────────────
    async def get(self, plan_id: str) -> dict[str, object] | None:
        row = await self._session.get(ActionPlanModel, plan_id)
        return _plan_to_dict(row) if row else None

    async def list_steps(self, plan_id: str) -> list[dict[str, object]]:
        rows = (await self._session.execute(
            select(ActionPlanStepModel)
            .where(ActionPlanStepModel.plan_id == plan_id)
            .order_by(ActionPlanStepModel.sort_order, ActionPlanStepModel.title)
        )).scalars().all()
        return [_step_to_dict(r) for r in rows]

    async def create_step(self, plan_id: str, data: dict[str, object]) -> dict[str, object]:
        row = ActionPlanStepModel(id=str(uuid.uuid4()), plan_id=plan_id, **_coerce_dates(data))
        self._session.add(row)
        await self._session.flush()
        return _step_to_dict(row)

    async def update_step(self, step_id: str, data: dict[str, object]) -> dict[str, object] | None:
        row = await self._session.get(ActionPlanStepModel, step_id)
        if row is None:
            return None
        for k, v in _coerce_dates(data).items():
            setattr(row, k, v)
        await self._session.flush()
        return _step_to_dict(row)

    async def delete_step(self, step_id: str) -> None:
        await self._session.execute(delete(ActionPlanStepModel).where(ActionPlanStepModel.id == step_id))
