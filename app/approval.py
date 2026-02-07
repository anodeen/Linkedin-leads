from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .messaging import MessageDraft


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(slots=True)
class DraftApproval:
    lead_id: int
    revision_id: int
    draft: MessageDraft
    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer: str | None = None
    review_notes: str | None = None
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: datetime | None = None


class ApprovalWorkflow:
    """PRD Step 4: require human approval before send."""

    def __init__(self) -> None:
        self._next_revision_id = 1
        self._items: dict[int, DraftApproval] = {}

    def submit(self, lead_id: int, draft: MessageDraft) -> DraftApproval:
        item = DraftApproval(lead_id=lead_id, revision_id=self._next_revision_id, draft=draft)
        self._items[item.revision_id] = item
        self._next_revision_id += 1
        return item

    def review(
        self,
        revision_id: int,
        reviewer: str,
        approve: bool,
        review_notes: str | None = None,
    ) -> DraftApproval:
        item = self._items.get(revision_id)
        if item is None:
            raise ValueError(f"revision_id {revision_id} not found")
        if item.status != ApprovalStatus.PENDING:
            raise ValueError(f"revision_id {revision_id} already reviewed")

        item.status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
        item.reviewer = reviewer.strip()
        item.review_notes = review_notes
        item.reviewed_at = datetime.now(timezone.utc)
        return item

    def is_send_allowed(self, lead_id: int) -> bool:
        return self.get_latest_approved(lead_id) is not None

    def get_latest_approved(self, lead_id: int) -> DraftApproval | None:
        approved = [
            item
            for item in self._items.values()
            if item.lead_id == lead_id and item.status == ApprovalStatus.APPROVED
        ]
        if not approved:
            return None
        return max(approved, key=lambda item: item.revision_id)

    def list_all(self) -> list[DraftApproval]:
        return sorted(self._items.values(), key=lambda item: item.revision_id)
