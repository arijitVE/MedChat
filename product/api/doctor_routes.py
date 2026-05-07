from uuid import UUID
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from pipeline_b.engines.query_classifier import classify
from pipeline_b.schemas.output import ReasoningResult, RetrievalResult, TrendResult
from pipeline_b.schemas.query import ClassifiedQuery, PersonaType, QueryType
from pipeline_b.services import reasoning_service, retrieval_service, trend_service
from product.auth.rate_limit import check_upload_rate_limit
from product.auth.role_guard import require_role
from product.schemas.assignment import AssignmentRequest, AssignmentResponse
from product.schemas.notification import NotificationItem, NotificationList
from product.schemas.report import ReportStatusResponse
from product.schemas.user import PatientProfile, UserProfile
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


router = APIRouter(prefix="/doctor", tags=["doctor"])


class DoctorQueryRequest(BaseModel):
    text: str
    patient_id: UUID
    filters: dict | None = None


@router.post("/upload")
async def upload_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    patient_uid: Optional[str] = Form(None),
    patient_email: Optional[str] = Form(None),
    force: bool = Query(default=False),
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    check_upload_rate_limit(str(current_user.user_id), db)
    return await upload_service.upload_report(
        current_user.user_id,
        "doctor",
        file,
        db,
        patient_uid=patient_uid,
        patient_email=patient_email,
        force=force,
        background_tasks=background_tasks,
    )


@router.put("/reports/{report_id}/reupload")
async def reupload_report(
    report_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force: bool = Query(default=False),
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    check_upload_rate_limit(str(current_user.user_id), db)
    return await upload_service.reupload_report(
        report_id,
        current_user.user_id,
        "doctor",
        file,
        db,
        force=force,
        background_tasks=background_tasks,
    )


@router.get("/reports/{report_id}")
def get_report(
    report_id: UUID,
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return report_service.get_report_for_doctor(report_id, current_user.user_id, db)


@router.post("/reports/{report_id}/release", response_model=ReportStatusResponse)
def release_report(
    report_id: UUID,
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return report_service.release_report_to_patient(report_id, current_user.user_id, db)


@router.get("/reports/{report_id}/fields", response_model=list[FieldStatus])
def get_report_fields(
    report_id: UUID,
    current_user: UserProfile = Depends(require_role("doctor")),
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
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return verification_service.verify_field(
        str(report_id),
        field_name,
        body,
        current_user,
        db,
    )


@router.post("/assignments", response_model=AssignmentResponse)
def create_assignment(
    body: AssignmentRequest,
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    if body.assigned_by != "doctor":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="assigned_by must be doctor")
    return assignment_service.create_assignment(
        current_user.user_id,
        body.patient_id,
        body.assigned_by,
        db,
        initiator_id=current_user.user_id,
    )


@router.get("/assignments", response_model=list[AssignmentResponse])
def list_assignments(
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return assignment_service.list_doctor_assignments(current_user.user_id, db)


@router.put("/assignments/{assignment_id}/approve", response_model=AssignmentResponse)
def approve_assignment(
    assignment_id: UUID,
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return assignment_service.approve_assignment(assignment_id, current_user.user_id, db)


@router.put("/assignments/{assignment_id}/reject", response_model=AssignmentResponse)
def reject_assignment(
    assignment_id: UUID,
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return assignment_service.reject_assignment(assignment_id, current_user.user_id, db)


@router.post("/query")
def doctor_query(
    body: DoctorQueryRequest,
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
) -> RetrievalResult | ReasoningResult | TrendResult:
    report_service.ensure_doctor_patient_access(current_user.user_id, body.patient_id, db)

    classified = classify(body.text, PersonaType.doctor)
    classified.patient_id = str(body.patient_id)
    classified.filters = body.filters

    if classified.query_type == QueryType.retrieval:
        result = retrieval_service.handle_retrieval_query(classified, db)
        records = [
            record
            for record in result.records
            if str(record.get("patient_id")) == str(body.patient_id)
        ]
        return RetrievalResult(
            records=records,
            total_count=len(records),
            query_interpretation=result.query_interpretation,
            retrieval_type=result.retrieval_type,
        )
    if classified.query_type == QueryType.trend:
        return trend_service.handle_trend_query(classified, str(body.patient_id), db)
    return reasoning_service.handle_reasoning_query(classified, str(body.patient_id), db)


@router.get("/patients/{patient_id}/trend", response_model=TrendResult)
def patient_trend(
    patient_id: UUID,
    field_name: str = Query(...),
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    report_service.ensure_doctor_patient_access(current_user.user_id, patient_id, db)
    classified = ClassifiedQuery(
        text=f"{field_name} trend over time",
        persona=PersonaType.doctor,
        patient_id=str(patient_id),
        query_type=QueryType.trend,
        confidence=1.0,
        classification_method="rule",
    )
    return trend_service.handle_trend_query(classified, str(patient_id), db)


@router.get("/patients/{patient_id}/analytics")
def patient_analytics(
    patient_id: UUID,
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    report_service.ensure_doctor_patient_access(current_user.user_id, patient_id, db)
    return report_service.get_patient_sql_analytics(patient_id, db)


@router.get("/patients/search", response_model=list[PatientProfile])
def search_patients(
    q: str = Query(...),
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return search_service.search_patients_for_doctor(current_user.user_id, q, db)


@router.get("/notifications", response_model=NotificationList)
def list_notifications(
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return notification_service.list_notifications(current_user.user_id, db)


@router.put("/notifications/{notification_id}/read", response_model=NotificationItem)
def mark_notification_read(
    notification_id: UUID,
    current_user: UserProfile = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    return notification_service.mark_notification_read(
        notification_id,
        current_user.user_id,
        db,
    )
