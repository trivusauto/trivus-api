class QualificationContext:
    def __init__(self, stage_ids_at_or_after: set[str], leads_with_history: set[str]) -> None:
        self._at_or_after = stage_ids_at_or_after
        self._leads_with_history = leads_with_history

    def passed(self, lead: dict[str, object]) -> bool:
        if lead.get("id") in self._leads_with_history:
            return True
        return bool(lead.get("stage_id") and str(lead["stage_id"]) in self._at_or_after)
