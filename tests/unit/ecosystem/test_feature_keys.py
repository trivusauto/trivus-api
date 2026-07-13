from src.modules.ecosystem.domain.feature_keys import ALL_FEATURE_KEYS, is_valid_feature_key, list_feature_keys


def test_known_keys_exist() -> None:
    for key in ("crm.kanban", "agenda", "metrics.reports.costs", "bulk_send"):
        assert is_valid_feature_key(key)


def test_invalid_key() -> None:
    assert is_valid_feature_key("nao.existe") is False


def test_list_has_labels() -> None:
    items = list_feature_keys()
    assert all("key" in i and "label" in i and "kind" in i for i in items)
    assert len(items) == len(ALL_FEATURE_KEYS)
