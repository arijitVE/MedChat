from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from product.schemas.notification import NotificationItem, NotificationList
from shared.logger import get_logger


logger = get_logger(__name__)


def create_notification(
    recipient_id: str | UUID,
    sender_id: str | UUID | None,
    notif_type: str,
    title: str,
    message: str,
    report_id: str | UUID | None,
    db: Session,
) -> None:
    """Insert notification row. Never raises — log errors silently."""
    try:
        db.execute(
            text(
                """
                INSERT INTO notifications (
                    recipient_id, sender_id, type, title, message, report_id
                )
                VALUES (
                    :recipient_id, :sender_id, :type, :title, :message, :report_id
                )
                """
            ),
            {
                "recipient_id": recipient_id,
                "sender_id": sender_id,
                "type": notif_type,
                "title": title,
                "message": message,
                "report_id": report_id,
            },
        )
    except Exception as exc:
        logger.warning(
            "notification_insert_failed",
            recipient_id=str(recipient_id),
            notification_type=notif_type,
            error=str(exc),
        )


def notify_report_uploaded(patient_id, doctor_id, report_id, db: Session) -> None:
    create_notification(
        patient_id,
        doctor_id,
        "REPORT_UPLOADED",
        "Report uploaded",
        "A doctor uploaded a report for you.",
        report_id,
        db,
    )


def notify_report_processed(patient_id, report_id, hitl_required, db: Session) -> None:
    message = (
        "Your report needs verification before release."
        if hitl_required
        else "Your report has been processed."
    )
    create_notification(
        patient_id,
        None,
        "REPORT_PROCESSED",
        "Report processed",
        message,
        report_id,
        db,
    )


def notify_report_released(patient_id, report_id, db: Session) -> None:
    create_notification(
        patient_id,
        None,
        "REPORT_RELEASED",
        "Report released",
        "Your report is now available.",
        report_id,
        db,
    )


def notify_field_verified(target_user_id, field_name, verifier_role, db: Session) -> None:
    create_notification(
        target_user_id,
        None,
        "FIELD_VERIFIED",
        "Field verified",
        f"{field_name} was verified by {verifier_role}.",
        None,
        db,
    )


def notify_assignment_request(target_user_id, requester_name, db: Session) -> None:
    create_notification(
        target_user_id,
        None,
        "ASSIGNMENT_REQUEST",
        "Assignment request",
        f"{requester_name} requested a doctor-patient assignment.",
        None,
        db,
    )


def notify_assignment_approved(target_user_id, db: Session) -> None:
    create_notification(
        target_user_id,
        None,
        "ASSIGNMENT_APPROVED",
        "Assignment approved",
        "A doctor-patient assignment was approved.",
        None,
        db,
    )


def notify_re_upload(patient_id, doctor_id, report_id, db: Session) -> None:
    create_notification(
        patient_id,
        doctor_id,
        "RE_UPLOAD_DONE",
        "Report re-uploaded",
        "A report was re-uploaded.",
        report_id,
        db,
    )


def list_notifications(recipient_id: str | UUID, db: Session) -> NotificationList:
    rows = db.execute(
        text(
            """
            SELECT notification_id, recipient_id, sender_id, type, title,
                   message, report_id, is_read, created_at
            FROM notifications
            WHERE recipient_id = :recipient_id
            ORDER BY created_at DESC
            """
        ),
        {"recipient_id": recipient_id},
    ).mappings().all()
    unread_count = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM notifications
            WHERE recipient_id = :recipient_id
              AND is_read = FALSE
            """
        ),
        {"recipient_id": recipient_id},
    ).scalar_one()
    return NotificationList(
        notifications=[NotificationItem(**row) for row in rows],
        unread_count=unread_count,
    )


def mark_notification_read(
    notification_id: str | UUID,
    recipient_id: str | UUID,
    db: Session,
) -> NotificationItem:
    row = db.execute(
        text(
            """
            UPDATE notifications
            SET is_read = TRUE
            WHERE notification_id = :notification_id
              AND recipient_id = :recipient_id
            RETURNING notification_id, recipient_id, sender_id, type, title,
                      message, report_id, is_read, created_at
            """
        ),
        {
            "notification_id": notification_id,
            "recipient_id": recipient_id,
        },
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.commit()
    return NotificationItem(**row)
