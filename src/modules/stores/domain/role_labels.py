SHOP_ROLE_KEYS = ("sdr", "vendedor", "administrativo", "gerente")
DEFAULT_SHOP_ROLE_LABELS: dict[str, str] = {
    "sdr": "SDR", "vendedor": "Vendedor", "administrativo": "Administrativo", "gerente": "Gerente",
}
_MAX_LEN = 80


def merge_shop_role_labels(db: object) -> dict[str, str]:
    out = dict(DEFAULT_SHOP_ROLE_LABELS)
    if isinstance(db, dict):
        for k in SHOP_ROLE_KEYS:
            v = db.get(k)
            if isinstance(v, str):
                t = v.strip()[:_MAX_LEN]
                if t:
                    out[k] = t
    return out
