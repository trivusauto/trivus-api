from src.modules.webhook.domain.phone import Phone

p = Phone()


def test_normalize() -> None:
    assert p.normalize_br("(11) 99999-9999") == "5511999999999"
    assert p.normalize_br("5511999999999") == "5511999999999"
    assert p.normalize_br("123") is None
    assert p.normalize_br("1133334444") is None


def test_extract_identity() -> None:
    assert p.extract_identity({"phone": "5544999999999@c.us"}) == ("44999999999", None)
    assert p.extract_identity({"phone": "63312750448861@lid"}) == (None, "63312750448861")


def test_variants() -> None:
    assert p.match_variants("44999999999") == ["44999999999", "4499999999"]
    assert p.match_variants("4499999999") == ["4499999999", "44999999999"]


def test_parse_many() -> None:
    r = p.parse_many("(11) 99999-9999, 11999999999\n5511988887777 abc")
    assert r["phones"] == ["5511999999999", "5511988887777"]
    assert r["duplicated"] == 1
