# shared/db/models/hitl.py — HITL queue + reviewer decisions
# Tracks documents requiring human review and records reviewer actions.

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from shared.db.base import Base


class HITLQueueItem(Base):
    """ORM model for the HITL review queue.

    When a document's confidence falls below thresholds, a queue item is
    created. Reviewers approve/edit/reject fields through the HITL API
    endpoints.
    """

    __tablename__ = "hitl_queue"

    # ------ Primary Key ------
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # ------ Job Reference ------
    job_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="Job requiring review",
    )
    patient_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
        comment="Patient identifier for filtering",
    )

    # ------ Review State ------
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending_review",
        comment="pending_review | in_review | reviewed | rejected",
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Higher = more urgent. Computed from confidence scores.",
    )

    # ------ HITL Reasons ------
    hitl_reasons: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="JSON list of reasons HITL was triggered",
    )
    hitl_field_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Number of fields flagged for review",
    )

    # ------ Review Metadata ------
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True,
        comment="Reviewer username or ID",
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When review was completed",
    )
    review_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Reviewer's notes or comments",
    )

    # ------ Timestamps ------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="When the queue item was created",
    )

    # ------ Constraints ------
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_hitl_queue_job_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<HITLQueueItem job_id={self.job_id!r} status={self.status!r} "
            f"priority={self.priority}>"
        )


# ---------------------------------------------------------------------------
# Upsert helper
# ---------------------------------------------------------------------------


def upsert_hitl_queue_item(db: Session, job_id: str, **fields: Any) -> None:
    """Upsert a HITL queue item keyed on job_id.

    Uses INSERT ... ON CONFLICT (job_id) DO UPDATE.
    """
    values = {"job_id": job_id, **fields}
    update_values = {k: v for k, v in fields.items()}

    stmt = (
        pg_insert(HITLQueueItem)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["job_id"],
            set_=update_values,
        )
    )
    db.execute(stmt)
    db.flush()
