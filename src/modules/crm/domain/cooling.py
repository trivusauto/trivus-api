class Cooling:
    def active_rule(self, hours_in_column: float, rules: list[dict[str, object]]) -> dict[str, object] | None:
        active: dict[str, object] | None = None
        for r in rules or []:
            if hours_in_column >= int(str(r["hours_threshold"])):
                active = r
        return active
