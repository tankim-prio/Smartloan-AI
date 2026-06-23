import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.database import get_db
from app.models.application import Application
from app.models.application_document import ApplicationDocument
from app.models.extracted_field import ExtractedField
from app.models.extracted_text import ExtractedText
from app.models.notification import Notification
from app.models.user import User
from app.schemas.application import (
    ApplicationDocumentResponse,
    ApplicationResponse,
    ApplicationStepOneCreate,
    ApplicationStepTwoUpdate,
    ExtractedFieldResponse,
    ExtractedTextResponse,
)
from app.services.extraction_service import extract_basic_fields, extract_text_from_pdf
from app.services.pdf_service import generate_application_pdf


router = APIRouter(prefix="/applications", tags=["Applications"])


ALLOWED_DOCUMENT_TYPES = {
    "salary_certificate",
    "tin_certificate",
    "nid",
    "passport",
    "photo",
    "loan_application",
    "generated_pdf",
}

ALLOWED_FILE_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
}


def get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return application


def ensure_owner_or_admin(application: Application, current_user: User):
    if current_user.role == "admin":
        return

    if application.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this application",
        )


@router.post("/step-1", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_step_one_application(
    data: ApplicationStepOneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = Application(
        user_id=current_user.id,
        first_name=data.first_name,
        last_name=data.last_name,
        father_name=data.father_name,
        mother_name=data.mother_name,
        age=data.age,
        phone=data.phone,
        email=data.email,
        address=data.address,
        status="draft",
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return application


@router.get("/my", response_model=list[ApplicationResponse])
def get_my_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Application)
        .filter(Application.user_id == current_user.id)
        .order_by(Application.id.desc())
        .all()
    )


@router.get("/admin/all", response_model=list[ApplicationResponse])
def get_all_applications_for_admin(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return db.query(Application).order_by(Application.id.desc()).all()


@router.patch("/{application_id}/step-2", response_model=ApplicationResponse)
def update_step_two_application(
    application_id: int,
    data: ApplicationStepTwoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    if application.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft applications can be updated",
        )

    application.occupation = data.occupation
    application.monthly_income = data.monthly_income

    db.commit()
    db.refresh(application)

    return application


@router.post("/{application_id}/documents", response_model=ApplicationDocumentResponse)
def upload_application_document(
    application_id: int,
    document_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Allowed: {sorted(ALLOWED_DOCUMENT_TYPES)}",
        )

    original_name = file.filename or "uploaded_file"
    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: PDF, JPG, JPEG, PNG",
        )

    upload_dir = Path("uploads") / "applications" / str(application_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_file_name = f"{document_type}_{uuid4().hex}{extension}"
    file_path = upload_dir / stored_file_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document = ApplicationDocument(
        application_id=application.id,
        document_type=document_type,
        original_file_name=original_name,
        stored_file_name=stored_file_name,
        file_path=str(file_path),
        content_type=file.content_type,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.post("/{application_id}/generate-pdf", response_model=ApplicationDocumentResponse)
def generate_pdf_for_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    if not application.occupation or application.monthly_income is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete Step 2 before generating PDF",
        )

    output_dir = Path("uploads") / "applications" / str(application_id)
    file_name = f"generated_application_{application_id}_{uuid4().hex}.pdf"
    output_path = output_dir / file_name

    generate_application_pdf(application, output_path)

    document = ApplicationDocument(
        application_id=application.id,
        document_type="generated_pdf",
        original_file_name=file_name,
        stored_file_name=file_name,
        file_path=str(output_path),
        content_type="application/pdf",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.post("/{application_id}/extract-text", response_model=ExtractedTextResponse)
def extract_text_from_application_document(
    application_id: int,
    document_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    document = (
        db.query(ApplicationDocument)
        .filter(
            ApplicationDocument.id == document_id,
            ApplicationDocument.application_id == application_id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found for this application",
        )

    try:
        raw_text = extract_text_from_pdf(document.file_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored file not found",
        )

    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text could be extracted from this document",
        )

    extracted_text = ExtractedText(
        application_id=application_id,
        document_id=document_id,
        raw_text=raw_text,
    )

    db.add(extracted_text)
    db.commit()
    db.refresh(extracted_text)

    return extracted_text


@router.post("/{application_id}/extract-fields", response_model=list[ExtractedFieldResponse])
def extract_fields_from_latest_text(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    latest_text = (
        db.query(ExtractedText)
        .filter(ExtractedText.application_id == application_id)
        .order_by(ExtractedText.id.desc())
        .first()
    )

    if not latest_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extracted text found. Run extract-text first.",
        )

    fields = extract_basic_fields(latest_text.raw_text)

    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields could be extracted from latest text",
        )

    db.query(ExtractedField).filter(
        ExtractedField.application_id == application_id
    ).delete()

    created_fields = []

    for field_name, field_value in fields.items():
        item = ExtractedField(
            application_id=application_id,
            field_name=field_name,
            field_value=field_value,
            confidence_score=1.0,
        )
        db.add(item)
        created_fields.append(item)

    db.commit()

    for item in created_fields:
        db.refresh(item)

    return created_fields


@router.get("/{application_id}/extracted-texts", response_model=list[ExtractedTextResponse])
def get_extracted_texts(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    return (
        db.query(ExtractedText)
        .filter(ExtractedText.application_id == application_id)
        .order_by(ExtractedText.id.desc())
        .all()
    )


@router.get("/{application_id}/extracted-fields", response_model=list[ExtractedFieldResponse])
def get_extracted_fields(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    return (
        db.query(ExtractedField)
        .filter(ExtractedField.application_id == application_id)
        .order_by(ExtractedField.id.asc())
        .all()
    )


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application_details(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    return application


@router.get("/{application_id}/documents", response_model=list[ApplicationDocumentResponse])
def get_application_documents(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    return (
        db.query(ApplicationDocument)
        .filter(ApplicationDocument.application_id == application_id)
        .order_by(ApplicationDocument.id.desc())
        .all()
    )


@router.post("/{application_id}/send-review", response_model=ApplicationResponse)
def send_application_to_review(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    if application.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft applications can be sent for review",
        )

    missing_fields = []

    if not application.occupation:
        missing_fields.append("occupation")

    if application.monthly_income is None:
        missing_fields.append("monthly_income")

    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Application is incomplete",
                "missing_fields": missing_fields,
            },
        )

    document_count = (
        db.query(ApplicationDocument)
        .filter(ApplicationDocument.application_id == application_id)
        .count()
    )

    if document_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one document must be uploaded before sending for review",
        )

    application.status = "pending_review"

    notification = Notification(
        user_id=application.user_id,
        application_id=application.id,
        title="Application Submitted",
        message="Your application has been sent for admin review.",
        is_read=False,
    )

    db.add(notification)
    db.commit()
    db.refresh(application)

    return application
