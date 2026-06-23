from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.application import Application
from app.models.application_document import ApplicationDocument


router = APIRouter(prefix="/review-workflow", tags=["Review Workflow"])
compat_router = APIRouter(prefix="/applications", tags=["Review Compatibility"])


def is_admin(current_user) -> bool:
    return str(getattr(current_user, "role", "") or "").lower() == "admin"


def get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return application


def check_owner_or_admin(current_user, application: Application) -> None:
    if is_admin(current_user):
        return

    if getattr(application, "user_id", None) == getattr(current_user, "id", None):
        return

    raise HTTPException(status_code=403, detail="Not allowed")


def check_admin(current_user) -> None:
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")


def value(application: Application, field: str, default: Any = None) -> Any:
    return getattr(application, field, default)


def applicant_name(application: Application) -> str:
    first_name = str(value(application, "first_name", "") or "").strip()
    last_name = str(value(application, "last_name", "") or "").strip()
    full_name = f"{first_name} {last_name}".strip()

    if full_name:
        return full_name

    return str(value(application, "applicant_name", "") or "Unknown Applicant")


def serialize_application(application: Application) -> dict:
    return {
        "id": application.id,
        "status": value(application, "status", "draft"),
        "applicant_name": applicant_name(application),
        "first_name": value(application, "first_name", ""),
        "last_name": value(application, "last_name", ""),
        "father_name": value(application, "father_name", ""),
        "mother_name": value(application, "mother_name", ""),
        "age": value(application, "age", None),
        "phone": value(application, "phone", ""),
        "email": value(application, "email", ""),
        "address": value(application, "address", ""),
        "occupation": value(application, "occupation", ""),
        "monthly_income": value(application, "monthly_income", None),
        "user_id": value(application, "user_id", None),
    }


def serialize_document(document: ApplicationDocument) -> dict:
    return {
        "id": document.id,
        "document_type": getattr(document, "document_type", None),
        "original_file_name": getattr(document, "original_file_name", None),
        "file_name": getattr(document, "file_name", None),
        "stored_file_name": getattr(document, "stored_file_name", None),
        "file_path": getattr(document, "file_path", None),
        "stored_file_path": getattr(document, "stored_file_path", None),
        "content_type": getattr(document, "content_type", None),
        "mime_type": getattr(document, "mime_type", None),
        "file_size": getattr(document, "file_size", None) or getattr(document, "size_bytes", None),
    }


def serialize_detail(db: Session, application: Application) -> dict:
    documents = (
        db.query(ApplicationDocument)
        .filter(ApplicationDocument.application_id == application.id)
        .order_by(ApplicationDocument.id.desc())
        .all()
    )

    extracted_fields = {
        "application_id": application.id,
        "status": value(application, "status", "draft"),
        "applicant_name": applicant_name(application),
        "father_name": value(application, "father_name", ""),
        "mother_name": value(application, "mother_name", ""),
        "age": value(application, "age", None),
        "phone": value(application, "phone", ""),
        "email": value(application, "email", ""),
        "address": value(application, "address", ""),
        "occupation": value(application, "occupation", ""),
        "monthly_income": value(application, "monthly_income", None),
    }

    return {
        "application": serialize_application(application),
        "extracted_fields": extracted_fields,
        "documents": [serialize_document(document) for document in documents],
    }


def update_status(db: Session, application: Application, status: str) -> Application:
    application.status = status

    for field in ["updated_at", "review_requested_at", "reviewed_at"]:
        if hasattr(application, field):
            try:
                setattr(application, field, datetime.utcnow())
            except Exception:
                pass

    db.add(application)
    db.commit()
    db.refresh(application)

    return application


@compat_router.post("/{application_id}/send-review")
def send_review_compat(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_owner_or_admin(current_user, application)

    application = update_status(db, application, "pending_review")

    return {
        "sent": True,
        "message": "Application sent to review successfully.",
        "application": serialize_application(application),
    }


@router.post("/applications/{application_id}/send-review")
def send_review_direct(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_owner_or_admin(current_user, application)

    application = update_status(db, application, "pending_review")

    return {
        "sent": True,
        "message": "Application sent to review successfully.",
        "application": serialize_application(application),
    }


@router.get("/applications")
def list_review_applications(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    check_admin(current_user)

    # Important: show all applications so Review page never looks empty.
    # Pending ones appear first.
    applications = (
        db.query(Application)
        .order_by(Application.id.desc())
        .all()
    )

    data = [serialize_application(application) for application in applications]

    data.sort(
        key=lambda item: (
            0 if item["status"] == "pending_review" else 1,
            -int(item["id"]),
        )
    )

    return data


@router.get("/applications/{application_id}")
def get_review_detail(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    check_admin(current_user)

    application = get_application_or_404(db, application_id)

    return serialize_detail(db, application)


@router.patch("/applications/{application_id}/decision")
def review_decision(
    application_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    check_admin(current_user)

    application = get_application_or_404(db, application_id)

    decision = str(payload.get("decision", "") or "").strip().lower()

    if decision in ["approve", "approved"]:
        status = "approved"
    elif decision in ["refuse", "refused", "reject", "rejected"]:
        status = "refused"
    else:
        raise HTTPException(status_code=400, detail="Decision must be approved or refused")

    note = str(payload.get("note", "") or "").strip()

    if hasattr(application, "review_note"):
        try:
            application.review_note = note
        except Exception:
            pass

    if hasattr(application, "reviewed_by"):
        try:
            application.reviewed_by = getattr(current_user, "id", None)
        except Exception:
            pass

    application = update_status(db, application, status)

    return {
        "updated": True,
        "decision": status,
        "application": serialize_application(application),
    }
