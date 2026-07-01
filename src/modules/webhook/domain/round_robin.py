class RoundRobin:
    def eligible(self, sdrs: list[dict[str, object]]) -> list[str]:
        return [str(s["id"]) for s in (sdrs or []) if s.get("can_see_unassigned_leads")]

    def pick_next(self, sdr_ids: list[str], last_assigned: str | None) -> str | None:
        if not sdr_ids:
            return None
        if last_assigned in sdr_ids:
            return sdr_ids[(sdr_ids.index(last_assigned) + 1) % len(sdr_ids)]
        return sdr_ids[0]
