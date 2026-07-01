from src.modules.webhook.domain.phone import Phone
from src.modules.webhook.domain.round_robin import RoundRobin
from src.modules.webhook.infrastructure.repositories import WebhookLeadRepository, WebhookStoreRepository, WebhookUserRepository
from src.modules.crm.infrastructure.repositories import FunnelRepository, HistoryRepository, LeadRepository, StageRepository


class HandleZapiWebhookUseCase:
    def __init__(
        self,
        stores: WebhookStoreRepository,
        leads: WebhookLeadRepository,
        funnels: FunnelRepository,
        stages: StageRepository,
        leads_count: LeadRepository,
        users: WebhookUserRepository,
        history: HistoryRepository,
        phone: Phone,
        round_robin: RoundRobin,
    ) -> None:
        self._stores = stores
        self._leads = leads
        self._funnels = funnels
        self._stages = stages
        self._count = leads_count
        self._users = users
        self._history = history
        self._phone = phone
        self._rr = round_robin

    async def execute(self, token: str, body: dict[str, object]) -> dict[str, object]:
        store = await self._stores.get_by_webhook_token(token)
        if store is None:
            return {"ok": False, "reason": "unauthorized", "status": 401}
        if not (store.active and store.zapi_webhook_enabled and store.crm_enabled):  # type: ignore[union-attr]
            return {"ok": True, "skipped": "disabled"}
        if body.get("isGroup"):
            return {"ok": True, "skipped": "group"}
        if body.get("fromMe"):
            return {"ok": True, "skipped": "from_me"}
        if body.get("isNewsletter"):
            return {"ok": True, "skipped": "newsletter"}

        phone, lid = self._phone.extract_identity(body)
        if not phone and not lid:
            return {"ok": True, "skipped": "no_phone"}
        contact_name = (str(body.get("chatName") or body.get("senderName") or "")).strip() or phone or lid

        existing = await self._leads.find_duplicate(store.id, lid, self._phone.match_variants(phone))  # type: ignore[union-attr]
        if existing is not None:
            await self._leads.enrich(existing, lid, phone)
            return {"ok": True, "skipped": "duplicate", "lead_id": str(existing.id)}  # type: ignore[union-attr]

        funnel = await self._funnels.first_clone(store.id)  # type: ignore[union-attr]
        if funnel is None:
            return {"ok": False, "reason": "no_template_funnel", "status": 422}
        stage = await self._stages.first_of_funnel(funnel.id)
        if stage is None:
            return {"ok": False, "reason": "no_stage", "status": 422}

        assigned_to: str | None = None
        eligible = self._rr.eligible(await self._users.active_sdrs(store.id))  # type: ignore[union-attr]
        if eligible:
            assigned_to = self._rr.pick_next(eligible, store.last_assigned_sdr_id)  # type: ignore[union-attr]
            await self._stores.update_last_sdr(store.id, assigned_to)  # type: ignore[union-attr]

        sort_order = await self._count.count_in_stage(stage.id)
        lead = await self._leads.create({
            "stage_id": stage.id,
            "store_id": store.id,  # type: ignore[union-attr]
            "nome": contact_name,
            "telefone": phone or lid,
            "lid": lid,
            "sort_order": sort_order,
            "assigned_to": assigned_to,
            "funil": "receptivo",
        })
        await self._history.record(str(lead.id), stage.id)  # type: ignore[union-attr]
        return {"ok": True, "lead_id": str(lead.id), "assigned_to": assigned_to}  # type: ignore[union-attr]
