def _collect_haystack(body: dict[str, object]) -> str:
    """Junta os campos do payload onde o identificador da campanha pode aparecer
    (referral de anúncio CTWA, texto da mensagem, urls). Decisão D1: melhor esforço —
    validar com payload real da Z-API; o preenchimento manual é o fallback garantido."""
    parts: list[str] = []
    referral = body.get("referral")
    if isinstance(referral, dict):
        parts.extend(str(v) for v in referral.values() if v)
    text = body.get("text")
    if isinstance(text, dict):
        parts.append(str(text.get("message") or ""))
    for key in ("message", "sourceUrl", "adSourceUrl", "ctwaClid"):
        v = body.get(key)
        if v:
            parts.append(str(v))
    return " ".join(parts)


def match_campaign_by_link(campaigns: list[dict[str, object]], body: dict[str, object]) -> str | None:
    hay = _collect_haystack(body)
    if not hay:
        return None
    for c in campaigns:
        code = c.get("link_code")
        if code and str(code) in hay:
            return str(c["id"])
    return None
