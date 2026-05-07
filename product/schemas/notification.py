from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: UUID
    recipient_id: UUID
    sender_id: UUID | None = None
    type: str
    title: str
    message: str
    report_id: UUID | None = None
    is_read: bool = False
    created_at: datetime


class NotificationList(BaseModel):
    notifications: list[NotificationItem]
    unread_count: int

