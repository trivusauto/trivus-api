import re


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


class Phone:
    def normalize_br(self, value: str) -> str | None:
        d = _digits(str(value).strip())
        if not d:
            return None
        if d.startswith("55") and len(d) == 13:
            norm = d
        elif len(d) == 11:
            norm = "55" + d
        elif len(d) == 12 and d.startswith("55"):
            return None
        elif len(d) == 13 and not d.startswith("55"):
            return None
        elif len(d) not in (11, 13):
            return None
        else:
            norm = d
        number = norm[4:] if len(norm) == 13 else norm[2:]
        if len(number) != 9 or number[0] != "9":
            return None
        return norm if len(norm) == 13 else "55" + norm

    def extract_identity(self, body: dict[str, object]) -> tuple[str | None, str | None]:
        phone_field = str(body.get("phone") or "")
        is_lid = "@lid" in phone_field
        lid_source = str(body.get("chatLid") or body.get("senderLid") or (phone_field if is_lid else "") or "")
        lid = _digits(lid_source.split("@")[0]) or None
        phone = None
        if not is_lid:
            digits = _digits(phone_field.split("@")[0])
            if len(digits) in (12, 13) and digits.startswith("55"):
                digits = digits[2:]
            phone = digits or None
        return phone, lid

    def match_variants(self, phone: str | None) -> list[str]:
        d = _digits(str(phone or ""))
        if not d:
            return []
        variants = [d]
        if len(d) == 11 and d[2] == "9":
            variants.append(d[:2] + d[3:])
        elif len(d) == 10:
            variants.append(d[:2] + "9" + d[2:])
        return variants

    def parse_many(self, text: str) -> dict[str, object]:
        tokens = [t.strip() for t in re.split(r"[,;\n\r]+", text or "") if t.strip()]
        phones: list[str] = []
        seen: set[str] = set()
        invalid = duplicated = 0
        for tok in tokens:
            n = self.normalize_br(tok)
            if n:
                if n in seen:
                    duplicated += 1
                    continue
                seen.add(n)
                phones.append(n)
            elif len(_digits(tok)) >= 8:
                invalid += 1
        return {"phones": phones, "invalid": invalid, "duplicated": duplicated}
