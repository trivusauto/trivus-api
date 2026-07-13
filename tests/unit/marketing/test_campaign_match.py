from src.modules.marketing.domain.campaign_match import match_campaign_by_link

CAMPS: list[dict[str, object]] = [
    {"id": "c1", "link_code": "carro-popular-julho"},
    {"id": "c2", "link_code": "suv-agosto"},
]


def test_match_by_referral() -> None:
    body: dict[str, object] = {"referral": {"sourceUrl": "https://wa.me/55449?text=carro-popular-julho"}}
    assert match_campaign_by_link(CAMPS, body) == "c1"


def test_match_by_text() -> None:
    body: dict[str, object] = {"text": {"message": "Olá! Vi o anúncio suv-agosto e quero saber mais"}}
    assert match_campaign_by_link(CAMPS, body) == "c2"


def test_no_match() -> None:
    assert match_campaign_by_link(CAMPS, {"text": {"message": "oi"}}) is None
    assert match_campaign_by_link([], {"text": {"message": "carro-popular-julho"}}) is None
    assert match_campaign_by_link(CAMPS, {}) is None
