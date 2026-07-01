from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.role_labels import DEFAULT_SHOP_ROLE_LABELS, merge_shop_role_labels


def test_display_name() -> None:
    assert Store(id="1", nome_fantasia="Auto X").display_name() == "Auto X"


def test_role_labels_default() -> None:
    assert merge_shop_role_labels(None) == DEFAULT_SHOP_ROLE_LABELS


def test_role_labels_override_and_trim() -> None:
    out = merge_shop_role_labels({"sdr": "  Pré-vendas  ", "invalido": "x"})
    assert out["sdr"] == "Pré-vendas"
    assert out["vendedor"] == "Vendedor"
    assert "invalido" not in out
