from datetime import datetime
from typing import Any
import json
import re

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.application import Application
from app.models.application_document import ApplicationDocument


router = APIRouter(prefix="/review-workflow", tags=["Review Workflow"])
compat_router = APIRouter(prefix="/applications", tags=["Review Compatibility"])


BAD_SNAPSHOT_WORDS = [
    "my recent applications",
    "download fixed live pdf",
    "fixed live pdf",
    "use download",
    "approved",
    "draftuse",
    "send review",
    "create pdf",
    "apply page",
    "dashboard",
    "review page",
    "ml model",
    "reports",
    "ai pilot",
    "sign out",
]


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
                decided_by INTEGER,
                application_snapshot TEXT,
                document_ids TEXT
            )
            """
        )
    )
    db.commit()

    try:
        columns = db.execute(text("PRAGMA table_info(review_submissions)")).mappings().all()
        existing = {row["name"] for row in columns}

        if "application_snapshot" not in existing:
            db.execute(text("ALTER TABLE review_submissions ADD COLUMN application_snapshot TEXT"))

        if "document_ids" not in existing:
            db.execute(text("ALTER TABLE review_submissions ADD COLUMN document_ids TEXT"))

        db.commit()
    except Exception:
        db.rollback()


def is_admin(current_user) -> bool:
    return str(getattr(current_user, "role", "") or "").lower() == "admin"


def check_admin(current_user) -> None:
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")


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


def value(application: Application, field: str, default: Any = None) -> Any:
    return getattr(application, field, default)


def is_polluted_text(value: Any) -> bool:
    text_value = str(value or "").strip().lower()

    if not text_value:
        return False

    if len(text_value) > 90:
        return True

    return any(word in text_value for word in BAD_SNAPSHOT_WORDS)


def clean_short_text(value: Any, max_len: int = 80) -> str:
    text_value = str(value or "").strip()
    text_value = re.sub(r"\s+", " ", text_value)

    if not text_value:
        return ""

    if is_polluted_text(text_value):
        return ""

    return text_value[:max_len]


def clean_phone(value: Any) -> str:
    text_value = clean_short_text(value, 30)
    text_value = re.sub(r"[^\d+]", "", text_value)

    if len(text_value) < 5:
        return ""

    return text_value[:20]


def clean_email(value: Any) -> str:
    text_value = clean_short_text(value, 80)

    if "@" not in text_value:
        return ""

    return text_value[:80]


def clean_number(value: Any):
    if value in [None, ""]:
        return None

    try:
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return None


def applicant_name(application: Application) -> str:
    first_name = clean_short_text(value(application, "first_name", ""), 40)
    last_name = clean_short_text(value(application, "last_name", ""), 40)
    full_name = f"{first_name} {last_name}".strip()

    if full_name:
        return full_name

    possible_name = clean_short_text(value(application, "applicant_name", ""), 80)

    return possible_name or "Unknown Applicant"


def serialize_application_live(application: Application) -> dict:
    return {
        "application_id": application.id,
        "id": application.id,
        "application_status": value(application, "status", "draft"),
        "applicant_name": applicant_name(application),
        "first_name": clean_short_text(value(application, "first_name", ""), 40),
        "last_name": clean_short_text(value(application, "last_name", ""), 40),
        "father_name": clean_short_text(value(application, "father_name", ""), 70),
        "mother_name": clean_short_text(value(application, "mother_name", ""), 70),
        "age": clean_number(value(application, "age", None)),
        "phone": clean_phone(value(application, "phone", "")),
        "email": clean_email(value(application, "email", "")),
        "address": clean_short_text(value(application, "address", ""), 120),
        "occupation": clean_short_text(value(application, "occupation", ""), 80),
        "monthly_income": clean_number(value(application, "monthly_income", None)),
        "user_id": value(application, "user_id", None),
    }


def clean_snapshot(snapshot: dict, application: Application) -> dict:
    live = serialize_application_live(application)

    if not isinstance(snapshot, dict):
        return live

    first_name = clean_short_text(snapshot.get("first_name"), 40) or live.get("first_name", "")
    last_name = clean_short_text(snapshot.get("last_name"), 40) or live.get("last_name", "")

    applicant_from_payload = clean_short_text(snapshot.get("applicant_name"), 80)
    applicant_from_names = f"{first_name} {last_name}".strip()

    if not applicant_from_payload:
        applicant_from_payload = applicant_from_names or live.get("applicant_name") or "Unknown Applicant"

    cleaned = {
        **live,
        "application_id": clean_number(snapshot.get("application_id")) or live["application_id"],
        "applicant_name": applicant_from_payload,
        "first_name": first_name,
        "last_name": last_name,
        "father_name": clean_short_text(snapshot.get("father_name"), 70) or live.get("father_name", ""),
        "mother_name": clean_short_text(snapshot.get("mother_name"), 70) or live.get("mother_name", ""),
        "age": clean_number(snapshot.get("age")) or live.get("age"),
        "phone": clean_phone(snapshot.get("phone")) or live.get("phone", ""),
        "email": clean_email(snapshot.get("email")) or live.get("email", ""),
        "address": clean_short_text(snapshot.get("address"), 120) or live.get("address", ""),
        "occupation": clean_short_text(snapshot.get("occupation"), 80) or live.get("occupation", ""),
        "monthly_income": clean_number(snapshot.get("monthly_income")) or live.get("monthly_income"),
        "loan_pdf_name": clean_short_text(snapshot.get("loan_pdf_name"), 100),
        "submitted_source": "apply_page_send_review",
    }

    return cleaned


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


def document_text(document: ApplicationDocument) -> str:
    values = []

    for field in [
        "document_type",
        "original_file_name",
        "file_name",
        "stored_file_name",
        "file_path",
        "stored_file_path",
    ]:
        item = getattr(document, field, None)

        if item:
            values.append(str(item))

    return " ".join(values).lower()


def has_any(text_value: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text_value for keyword in keywords)


def get_latest_important_document_ids(db: Session, application_id: int) -> list[int]:
    documents = (
        db.query(ApplicationDocument)
        .filter(ApplicationDocument.application_id == application_id)
        .order_by(ApplicationDocument.id.desc())
        .all()
    )

    categories = [
        [
            "generated_pdf",
            "loan_application",
            "loan application",
            "loan_application_pdf",
            "generated_application",
        ],
        [
            "photo",
            "profile",
            "scan_photo",
            "applicant_photo",
            "picture",
            "image",
        ],
        [
            "salary_certificate",
            "tin_certificate",
            "salary",
            "tin",
            "income",
            "payroll",
        ],
        [
            "passport",
            "nid",
            "identity",
            "national_id",
            "national id",
            "id_document",
            "id proof",
        ],
    ]

    selected_ids: list[int] = []

    for keywords in categories:
        for document in documents:
            if document.id in selected_ids:
                continue

            if has_any(document_text(document), keywords):
                selected_ids.append(document.id)
                break

    return selected_ids


def documents_by_ids(db: Session, document_ids: list[int]) -> list[ApplicationDocument]:
    if not document_ids:
        return []

    documents = (
        db.query(ApplicationDocument)
        .filter(ApplicationDocument.id.in_(document_ids))
        .all()
    )

    document_map = {document.id: document for document in documents}

    return [document_map[doc_id] for doc_id in document_ids if doc_id in document_map]


def snapshot_from_submission(submission: dict) -> dict | None:
    raw = submission.get("application_snapshot")

    if not raw:
        return None

    try:
        data = json.loads(raw)

        if isinstance(data, dict):
            return data
    except Exception:
        return None

    return None


def document_ids_from_submission(submission: dict) -> list[int]:
    raw = submission.get("document_ids")

    if not raw:
        return []

    try:
        data = json.loads(raw)

        if isinstance(data, list):
            return [int(item) for item in data if str(item).isdigit()]
    except Exception:
        return []

    return []


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


def create_review_submission(
    db: Session,
    application: Application,
    payload: dict | None = None,
) -> dict:
    ensure_review_table(db)

    payload = payload or {}
    snapshot_payload = payload.get("application_snapshot") or payload.get("snapshot") or {}

    snapshot = clean_snapshot(snapshot_payload, application)
    document_ids = get_latest_important_document_ids(db, application.id)

    created_at = now_text()

    result = db.execute(
        text(
            """
            INSERT INTO review_submissions (
                application_id,
                status,
                note,
                created_at,
                updated_at,
                application_snapshot,
                document_ids
            )
            VALUES (
                :application_id,
                'pending_review',
                '',
                :created_at,
                :updated_at,
                :application_snapshot,
                :document_ids
            )
            """
        ),
        {
            "application_id": application.id,
            "created_at": created_at,
            "updated_at": created_at,
            "application_snapshot": json.dumps(snapshot, ensure_ascii=False),
            "document_ids": json.dumps(document_ids),
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


def serialize_submission(db: Session, submission: dict) -> dict:
    application = get_application_or_404(db, int(submission["application_id"]))
    snapshot = clean_snapshot(snapshot_from_submission(submission) or {}, application)

    return {
        "id": int(submission["id"]),
        "submission_id": int(submission["id"]),
        "review_id": int(submission["id"]),
        "application_id": int(submission["application_id"]),
        "status": submission.get("status") or "pending_review",
        "review_status": submission.get("status") or "pending_review",
        "submitted_at": submission.get("created_at"),
        "updated_at": submission.get("updated_at"),
        "decided_at": submission.get("decided_at"),
        "review_note": submission.get("note") or "",
        **snapshot,
    }


def serialize_detail(db: Session, submission: dict) -> dict:
    application = get_application_or_404(db, int(submission["application_id"]))
    snapshot = clean_snapshot(snapshot_from_submission(submission) or {}, application)

    document_ids = document_ids_from_submission(submission)
    documents = documents_by_ids(db, document_ids)

    if not documents:
        documents = (
            db.query(ApplicationDocument)
            .filter(ApplicationDocument.application_id == application.id)
            .order_by(ApplicationDocument.id.desc())
            .limit(20)
            .all()
        )

    submission_data = serialize_submission(db, submission)

    application_data = {
        **snapshot,
        "id": int(submission["application_id"]),
        "application_id": int(submission["application_id"]),
        "status": value(application, "status", "draft"),
    }

    extracted_fields = {
        "submission_id": int(submission["id"]),
        "application_id": int(submission["application_id"]),
        "review_status": submission.get("status") or "pending_review",
        "application_status": value(application, "status", "draft"),
        "applicant_name": snapshot.get("applicant_name", ""),
        "father_name": snapshot.get("father_name", ""),
        "mother_name": snapshot.get("mother_name", ""),
        "age": snapshot.get("age"),
        "phone": snapshot.get("phone", ""),
        "email": snapshot.get("email", ""),
        "address": snapshot.get("address", ""),
        "occupation": snapshot.get("occupation", ""),
        "monthly_income": snapshot.get("monthly_income"),
        "loan_pdf_name": snapshot.get("loan_pdf_name", ""),
        "submitted_source": snapshot.get("submitted_source", ""),
        "submitted_at": submission.get("created_at"),
        "review_note": submission.get("note") or "",
    }

    return {
        "submission": submission_data,
        "application": application_data,
        "extracted_fields": extracted_fields,
        "documents": [serialize_document(document) for document in documents],
    }


@compat_router.post("/{application_id}/send-review")
def send_review_compat(
    application_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_owner_or_admin(current_user, application)

    update_application_status(db, application, "pending_review")
    submission = create_review_submission(db, application, payload)

    return {
        "sent": True,
        "message": "Application sent to review successfully.",
        "submission": serialize_submission(db, submission),
        "application": serialize_application_live(application),
    }


@router.post("/applications/{application_id}/send-review")
def send_review_direct(
    application_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_owner_or_admin(current_user, application)

    update_application_status(db, application, "pending_review")
    submission = create_review_submission(db, application, payload)

    return {
        "sent": True,
        "message": "Application sent to review successfully.",
        "submission": serialize_submission(db, submission),
        "application": serialize_application_live(application),
    }


@router.get("/submissions")
def list_review_submissions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    check_admin(current_user)
    ensure_review_table(db)

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

    note = clean_short_text(payload.get("note"), 500)
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
        "application": serialize_application_live(application),
    }


@router.post("/admin/cleanup-snapshots")
def cleanup_bad_review_snapshots(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    check_admin(current_user)
    ensure_review_table(db)

    rows = db.execute(text("SELECT * FROM review_submissions ORDER BY id ASC")).mappings().all()

    cleaned_count = 0

    for row in rows:
        submission = dict(row)
        application = get_application_or_404(db, int(submission["application_id"]))
        snapshot = snapshot_from_submission(submission) or {}

        cleaned_snapshot = clean_snapshot(snapshot, application)

        if cleaned_snapshot != snapshot:
            db.execute(
                text(
                    """
                    UPDATE review_submissions
                    SET application_snapshot = :application_snapshot,
                        updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                {
                    "application_snapshot": json.dumps(cleaned_snapshot, ensure_ascii=False),
                    "updated_at": now_text(),
                    "id": int(submission["id"]),
                },
            )
            cleaned_count += 1

    db.commit()

    return {
        "cleaned": True,
        "cleaned_count": cleaned_count,
    }


# Backward compatible routes
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
        submission = create_review_submission(db, application)
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
        submission = create_review_submission(db, application)
        submission_id = int(submission["id"])
    else:
        submission_id = int(row["id"])

    return decide_review_submission(
        submission_id=submission_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )
