import pytest

from src.modules.bulk_send.application.create import CreateBulkSendUseCase
from src.modules.webhook.domain.phone import Phone


class FakeSends:
    def __init__(self) -> None:
        self.data: dict | None = None

    async def create(self, data: dict) -> str:
        self.data = data
        return "bs1"


class FakeContacts:
    def __init__(self) -> None:
        self.rows: list[dict] | None = None

    async def create_many(self, rows: list[dict]) -> None:
        self.rows = rows


@pytest.mark.asyncio
async def test_create_dedups_and_persists() -> None:
    sends, contacts = FakeSends(), FakeContacts()
    uc = CreateBulkSendUseCase(sends, contacts, Phone(), n8n=None)
    res = await uc.execute({"title": "T", "message_template": "oi", "variations": ["A", "B"],
                            "phones": ["11999999999", "11999999999", "5511988887777"],
                            "delay_min_sec": 30, "delay_max_sec": 30})
    assert sends.data is not None and sends.data["total_contacts"] == 2
    assert res["stats"]["duplicated"] == 1
    assert contacts.rows is not None
    assert [c["variation_index"] for c in contacts.rows] == [0, 1]


@pytest.mark.asyncio
async def test_create_without_variations() -> None:
    sends, contacts = FakeSends(), FakeContacts()
    uc = CreateBulkSendUseCase(sends, contacts, Phone(), n8n=None)
    await uc.execute({"message_template": "oi", "phones": ["11999999999"]})
    assert sends.data is not None and sends.data["variation_1"] is None
    assert contacts.rows is not None and contacts.rows[0]["variation_index"] == 0
