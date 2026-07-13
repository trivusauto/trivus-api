from typing import cast

from src.modules.bulk_send.infrastructure.n8n_client import N8nClient
from src.modules.bulk_send.infrastructure.repository import BulkSendContactRepository, BulkSendRepository
from src.modules.webhook.domain.phone import Phone


class CreateBulkSendUseCase:
    def __init__(self, sends: BulkSendRepository, contacts: BulkSendContactRepository,
                 phone: Phone, n8n: N8nClient | None = None) -> None:
        self._sends = sends
        self._contacts = contacts
        self._phone = phone
        self._n8n = n8n

    async def execute(self, data: dict[str, object]) -> dict[str, object]:
        phones_input = cast(list[str], data.get("phones") or [])
        parsed = self._phone.parse_many("\n".join(phones_input))
        phones = cast(list[str], parsed["phones"])
        variations = cast(list[str], data.get("variations") or [])[:5]
        send_id = await self._sends.create({
            "title": data.get("title"), "message_template": data.get("message_template"),
            "status": "draft", "total_contacts": len(phones),
            "delay_min_sec": data.get("delay_min_sec", 30), "delay_max_sec": data.get("delay_max_sec", 30),
            "variation_1": variations[0] if len(variations) > 0 else None,
            "variation_2": variations[1] if len(variations) > 1 else None,
            "variation_3": variations[2] if len(variations) > 2 else None,
            "variation_4": variations[3] if len(variations) > 3 else None,
            "variation_5": variations[4] if len(variations) > 4 else None,
        })
        if phones:
            n = len(variations) or 1
            await self._contacts.create_many([
                {"bulk_send_id": send_id, "phone": p, "variation_index": i % n, "status": "pending"}
                for i, p in enumerate(phones)
            ])
        if self._n8n:
            await self._n8n.dispatch(send_id, data)
        return {"id": send_id,
                "stats": {"total": len(phones), "duplicated": parsed["duplicated"], "invalid": parsed["invalid"]}}
