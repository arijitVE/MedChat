from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from pipeline_b.schemas.output import PatientChatResult, TrendResult
from pipeline_b.schemas.query import ClassifiedQuery, PersonaType, QueryType
from pipeline_b.services import patient_service, trend_service
from product.auth.rate_limit import check_upload_rate_limit
from product.auth.role_guard import require_role
from product.schemas.assignment import AssignmentResponse
from product.schemas.notification import NotificationItem, NotificationList
from product.schemas.user import UserProfile
from product.schemas.verification import (
    FieldStatus,
    FieldVerificationRequest,
    VerificationResponse,
)
from product.services import (
    assignment_service,
    notification_service,
    report_service,
    search_service,
    upload_service,
    verification_service,
)
from shared.db.session import get_db


router = APIRouter(prefix="/patient", tags=["patient"])


class PatientChatRequest(BaseModel):
    text: str


@router.post("/upload")
async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force: bool = Query(default=False),
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    check_upload_rate_limit(str(current_user.user_id), db)
    return await upload_service.upload_report(
        current_user.user_id,
        "patient",
        file,
        db,
        patient_id=current_user.user_id,
        force=force,
        background_tasks=background_tasks,
    )


@router.put("/reports/{report_id}/reupload")
async def reupload_report(
    report_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force: bool = Query(default=False),
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    check_upload_rate_limit(str(current_user.user_id), db)
    return await upload_service.reupload_report(
        report_id,
        current_user.user_id,
        "patient",
        file,
        db,
        force=force,
        background_tasks=background_tasks,
    )


@router.get("/reports/search")
def search_reports(
    date: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    document_type: str | None = Query(default=None, alias="type"),
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    effective_date_from = date_from or date
    effective_date_to = date_to or date
    return search_service.search_reports_for_patient(
        current_user.user_id,
        effective_date_from,
        effective_date_to,
        document_type,
        db,
    )


@router.get("/reports/{report_id}")
def get_report(
    report_id: UUID,
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    return report_service.get_report_for_patient(report_id, current_user.user_id, db)


@router.get("/reports/{report_id}/eda")
def get_report_eda(
    report_id: UUID,
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    return report_service.get_report_eda(report_id, current_user.user_id, db)


@router.get("/reports/{report_id}/fields", response_model=list[FieldStatus])
def get_report_fields(
    report_id: UUID,
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    return verification_service.get_field_verification_status(
        str(report_id),
        db,
        requesting_user_role=current_user.role,
    )


@router.post(
    "/reports/{report_id}/fields/{field_name}/verify",
    response_model=VerificationResponse,
)
def verify_report_field(
    report_id: UUID,
    field_name: str,
    body: FieldVerificationRequest,
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    return verification_service.verify_field(
        str(report_id),
        field_name,
        body,
        current_user,
        db,
    )


class PatientAssignmentRequest(BaseModel):
    doctor_id: UUID
    patient_id: UUID
    assigned_by: str


@router.post("/assignments", response_model=AssignmentResponse)
def create_assignment(
    body: PatientAssignmentRequest,
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    if body.assigned_by != "patient":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="assigned_by must be patient")
    if str(body.patient_id) != str(current_user.user_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="patient_id must match current user")
    return assignment_service.create_assignment(
        body.doctor_id,
        body.patient_id,
        body.assigned_by,
        db,
        initiator_id=current_user.user_id,
    )


@router.get("/assignments", response_model=list[AssignmentResponse])
def list_assignments(
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    return assignment_service.list_patient_assignments(current_user.user_id, db)


@router.put("/assignments/{assignment_id}/approve", response_model=AssignmentResponse)
def approve_assignment(
    assignment_id: UUID,
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    return assignment_service.approve_assignment(assignment_id, current_user.user_id, db)


@router.put("/assignments/{assignment_id}/reject", response_model=AssignmentResponse)
def reject_assignment(
    assignment_id: UUID,
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    return assignment_service.reject_assignment(assignment_id, current_user.user_id, db)


@router.post("/chat", response_model=PatientChatResult)
def patient_chat(
    body: PatientChatRequest,
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    classified = ClassifiedQuery(
        text=body.text,
        persona=PersonaType.patient,
        patient_id=str(current_user.user_id),
        query_type=QueryType.patient_chat,
        confidence=1.0,
        classification_method="rule",
    )
    return patient_service.handle_patient_query(classified, str(current_user.user_id), db)


@router.get("/trends", response_model=TrendResult)
def patient_trend(
    field_name: str = Query(...),
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    classified = ClassifiedQuery(
        text=f"{field_name} trend over time",
        persona=PersonaType.patient,
        patient_id=str(current_user.user_id),
        query_type=QueryType.trend,
        confidence=1.0,
        classification_method="rule",
    )
    return trend_service.handle_trend_query(classified, str(current_user.user_id), db)


@router.get("/notifications", response_model=NotificationList)
def list_notifications(
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    return notification_service.list_notifications(current_user.user_id, db)


@router.put("/notifications/{notification_id}/read", response_model=NotificationItem)
def mark_notification_read(
    notification_id: UUID,
    current_user: UserProfile = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    return notification_service.mark_notification_read(
        notification_id,
        current_user.user_id,
        db,
    )
