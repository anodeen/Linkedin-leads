from threading import Lock

from .models import InboundLead, Lead


class LeadStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._items: list[Lead] = []
        self._next_id = 1

    def add_many(self, leads: list[InboundLead]) -> list[Lead]:
        with self._lock:
            created: list[Lead] = []
            for lead in leads:
                item = Lead(
                    id=self._next_id,
                    full_name=lead.full_name,
                    title=lead.title,
                    company=lead.company,
                    profile_url=lead.profile_url,
                    source=lead.source,
                )
                self._items.append(item)
                created.append(item)
                self._next_id += 1
            return created

    def list_all(self) -> list[Lead]:
        with self._lock:
            return list(self._items)
