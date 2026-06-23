from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.application import Application
from app.models.application_document import ApplicationDocument


router = APIRouter(prefix="/review-workflow", tags=["Review Workflow"])
compat_router = APIRouter(prefix="/applications", tags=["Review Compatibility"])


def now_text() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def ensure_review_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS review_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_review',
                note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                decided_at TEXT,
                decided_by INTEGER
            )
            """
        )
    )
    db.commit()


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
        "application_id": application.id,
        "id": application.id,
        "application_status": value(application, "status", "draft"),
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


def create_review_submission(db: Session, application_id: int) -> dict:
    ensure_review_table(db)

    created_at = now_text()

    result = db.execute(
        text(
            """
            INSERT INTO review_submissions (
                application_id,
                status,
                note,
                created_at,
                updated_at
            )
            VALUES (
                :application_id,
                'pending_review',
                '',
                :created_at,
                :updated_at
            )
            """
        ),
        {
            "application_id": application_id,
            "created_at": created_at,
            "updated_at": created_at,
        },
    )

    db.commit()

    submission_id = result.lastrowid

    row = db.execute(
        text("SELECT * FROM review_submissions WHERE id = :id"),
        {"id": submission_id},
    ).mappings().first()

    return dict(row)


def get_submission_or_404(db: Session, submission_id: int) -> dict:
    ensure_review_table(db)

    row = db.execute(
        text("SELECT * FROM review_submissions WHERE id = :id"),
        {"id": submission_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Review submission not found")

    return dict(row)


def update_application_status(db: Session, application: Application, status: str) -> Application:
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


def serialize_submission(db: Session, submission: dict) -> dict:
    application = get_application_or_404(db, int(submission["application_id"]))

    data = serialize_application(application)

    data.update(
        {
            "submission_id": int(submission["id"]),
            "review_id": int(submission["id"]),
            "status": submission.get("status") or "pending_review",
            "review_status": submission.get("status") or "pending_review",
            "submitted_at": submission.get("created_at"),
            "updated_at": submission.get("updated_at"),
            "decided_at": submission.get("decided_at"),
            "review_note": submission.get("note") or "",
        }
    )

    return data


def serialize_detail(db: Session, submission: dict) -> dict:
    application = get_application_or_404(db, int(submission["application_id"]))

    documents = (
        db.query(ApplicationDocument)
        .filter(ApplicationDocument.application_id == application.id)
        .order_by(ApplicationDocument.id.desc())
        .all()
    )

    extracted_fields = {
        "submission_id": int(submission["id"]),
        "application_id": application.id,
        "review_status": submission.get("status") or "pending_review",
        "application_status": value(application, "status", "draft"),
        "applicant_name": applicant_name(application),
        "father_name": value(application, "father_name", ""),
        "mother_name": value(application, "mother_name", ""),
        "age": value(application, "age", None),
        "phone": value(application, "phone", ""),
        "email": value(application, "email", ""),
        "address": value(application, "address", ""),
        "occupation": value(application, "occupation", ""),
        "monthly_income": value(application, "monthly_income", None),
        "submitted_at": submission.get("created_at"),
        "review_note": submission.get("note") or "",
    }

    return {
        "submission": serialize_submission(db, submission),
        "application": serialize_application(application),
        "extracted_fields": extracted_fields,
        "documents": [serialize_document(document) for document in documents],
    }


def seed_from_existing_applications_if_empty(db: Session) -> None:
    ensure_review_table(db)

    count = db.execute(text("SELECT COUNT(*) AS count FROM review_submissions")).mappings().first()["count"]

    if count:
        return

    applications = db.query(Application).order_by(Application.id.desc()).all()

    for application in applications:
        status = str(value(application, "status", "draft") or "draft")

        if status in ["approved", "refused", "rejected", "pending_review"]:
            created_at = now_text()

            db.execute(
                text(
                    """
                    INSERT INTO review_submissions (
                        application_id,
                        status,
                        note,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :application_id,
                        :status,
                        '',
                        :created_at,
                        :updated_at
                    )
                    """
                ),
                {
                    "application_id": application.id,
                    "status": "refused" if status == "rejected" else status,
                    "created_at": created_at,
                    "updated_at": created_at,
                },
            )

    db.commit()


@compat_router.post("/{application_id}/send-review")
def send_review_compat(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_owner_or_admin(current_user, application)

    update_application_status(db, application, "pending_review")
    submission = create_review_submission(db, application.id)

    return {
        "sent": True,
        "message": "Application sent to review successfully.",
        "submission": serialize_submission(db, submission),
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

    update_application_status(db, application, "pending_review")
    submission = create_review_submission(db, application.id)

    return {
        "sent": True,
        "message": "Application sent to review successfully.",
        "submission": serialize_submission(db, submission),
        "application": serialize_application(application),
    }


@router.get("/submissions")
def list_review_submissions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    check_admin(current_user)
    seed_from_existing_applications_if_empty(db)

    rows = db.execute(
        text(
            """
            SELECT *
            FROM review_submissions
            ORDER BY id DESC
            """
        )
    ).mappings().all()

    return [serialize_submission(db, dict(row)) for row in rows]


@router.get("/submissions/{submission_id}")
def get_review_submission_detail(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    check_admin(current_user)

    submission = get_submission_or_404(db, submission_id)

    return serialize_detail(db, submission)


@router.patch("/submissions/{submission_id}/decision")
def decide_review_submission(
    submission_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    check_admin(current_user)

    submission = get_submission_or_404(db, submission_id)
    application = get_application_or_404(db, int(submission["application_id"]))

    decision = str(payload.get("decision", "") or "").strip().lower()

    if decision in ["approve", "approved"]:
        status = "approved"
    elif decision in ["refuse", "refused", "reject", "rejected"]:
        status = "refused"
    else:
        raise HTTPException(status_code=400, detail="Decision must be approved or refused")

    note = str(payload.get("note", "") or "").strip()
    updated_at = now_text()

    db.execute(
        text(
            """
            UPDATE review_submissions
            SET status = :status,
                note = :note,
                updated_at = :updated_at,
                decided_at = :decided_at,
                decided_by = :decided_by
            WHERE id = :id
            """
        ),
        {
            "status": status,
            "note": note,
            "updated_at": updated_at,
            "decided_at": updated_at,
            "decided_by": getattr(current_user, "id", None),
            "id": submission_id,
        },
    )
    db.commit()

    update_application_status(db, application, status)

    updated_submission = get_submission_or_404(db, submission_id)

    return {
        "updated": True,
        "decision": status,
        "submission": serialize_submission(db, updated_submission),
        "application": serialize_application(application),
    }


# Backward-compatible routes for old ReviewPage code
@router.get("/applications")
def list_review_applications_compat(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return list_review_submissions(db=db, current_user=current_user)


@router.get("/applications/{application_id}")
def get_latest_submission_detail_by_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    check_admin(current_user)
    ensure_review_table(db)

    row = db.execute(
        text(
            """
            SELECT *
            FROM review_submissions
            WHERE application_id = :application_id
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"application_id": application_id},
    ).mappings().first()

    if not row:
        application = get_application_or_404(db, application_id)
        submission = create_review_submission(db, application.id)
        return serialize_detail(db, submission)

    return serialize_detail(db, dict(row))


@router.patch("/applications/{application_id}/decision")
def decide_latest_submission_by_application(
    application_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    check_admin(current_user)
    ensure_review_table(db)

    row = db.execute(
        text(
            """
            SELECT *
            FROM review_submissions
            WHERE application_id = :application_id
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"application_id": application_id},
    ).mappings().first()

    if not row:
        application = get_application_or_404(db, application_id)
        submission = create_review_submission(db, application.id)
        submission_id = int(submission["id"])
    else:
        submission_id = int(row["id"])

    return decide_review_submission(
        submission_id=submission_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )
