from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class OutcomeStatus(str, Enum):
    WON = "won"
    LOST = "lost"
    OPEN = "open"


@dataclass(slots=True)
class CRMOutcomeRecord:
    record_id: int
    lead_id: int
    crm_name: str
    status: OutcomeStatus
    deal_value: float | None = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class ScoringQualitySnapshot:
    total_labeled: int
    won_count: int
    high_score_count: int
    high_score_win_rate: float


class CRMOutcomeSync:
    """PRD Step 7: single CRM outcome sync for label feedback loops."""

    def __init__(self, default_crm: str = "hubspot") -> None:
        self.default_crm = default_crm
        self._next_id = 1
        self._records: list[CRMOutcomeRecord] = []

    def sync_outcome(
        self,
        lead_id: int,
        status: OutcomeStatus,
        deal_value: float | None = None,
        crm_name: str | None = None,
    ) -> CRMOutcomeRecord:
        if deal_value is not None and deal_value < 0:
            raise ValueError("deal_value cannot be negative")
        record = CRMOutcomeRecord(
            record_id=self._next_id,
            lead_id=lead_id,
            crm_name=(crm_name or self.default_crm),
            status=status,
            deal_value=deal_value,
        )
        self._next_id += 1
        self._records.append(record)
        return record

    def list_outcomes(self, lead_id: int | None = None) -> list[CRMOutcomeRecord]:
        if lead_id is None:
            return list(self._records)
        return [record for record in self._records if record.lead_id == lead_id]

    def purge_lead(self, lead_id: int) -> int:
        before = len(self._records)
        self._records = [record for record in self._records if record.lead_id != lead_id]
        return before - len(self._records)


    def purge_older_than(self, cutoff) -> int:
        before = len(self._records)
        self._records = [record for record in self._records if record.captured_at >= cutoff]
        return before - len(self._records)
