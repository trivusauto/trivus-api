from typing import cast

from src.shared.domain.errors import DomainError

_STATUS_BY_EVENT: dict[str, str | None] = {"payment_confirmed": "active", "payment_failed": "suspended",
                                           "payment_overdue": "suspended", "payment_refunded": None}
_PAYMENT_STATUS = {"payment_confirmed": "confirmed", "payment_failed": "failed",
                   "payment_overdue": "overdue", "payment_refunded": "refunded"}


class HandleBillingEventUseCase:
    """Recebe eventos do framework de pagamentos do dono (E1): persiste SEMPRE em
    subscription_payments; transiciona o status só quando billing_mode = gateway."""

    def __init__(self, subscriptions, payments) -> None:  # type: ignore[no-untyped-def]
        self._subs = subscriptions
        self._payments = payments

    async def execute(self, event: dict[str, object]) -> dict[str, object]:
        event_type = str(event.get("event_type") or "")
        if event_type not in _STATUS_BY_EVENT:
            raise DomainError(f"event_type desconhecido: {event_type}")
        sub = await self._subs.get_or_raise(event["subscription_id"])
        payment = await self._payments.create({
            "subscription_id": sub["id"], "external_id": event.get("external_id"),
            "gateway": event.get("gateway"), "event_type": event_type,
            "status": _PAYMENT_STATUS[event_type], "amount": event.get("amount"),
            "payload": event.get("raw") or {},
        })
        new_status = _STATUS_BY_EVENT[event_type]
        if new_status and sub.get("billing_mode") == "gateway":
            await self._subs.update(str(sub["id"]), {"status": new_status})
        return cast(dict[str, object], payment)
