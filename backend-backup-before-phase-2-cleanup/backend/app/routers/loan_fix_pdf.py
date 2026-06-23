
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.application import Application
from app.models.application_document import ApplicationDocument


router = APIRouter(prefix="/loan-fix", tags=["Loan Fix"])

OUTPUT_DIR = Path("uploads") / "fixed_live_pdfs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def safe(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def money(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"BDT {float(value):,.2f}"
    except Exception:
        return str(value)


def update_application_from_payload(application: Application, payload: dict):
    allowed_fields = [
        "first_name",
        "last_name",
        "father_name",
        "mother_name",
        "age",
        "phone",
        "email",
        "address",
        "occupation",
        "monthly_income",
    ]

    for field in allowed_fields:
        if field not in payload:
            continue

        value = payload.get(field)

        if field == "age" and value not in [None, ""]:
            value = int(value)

        if field == "monthly_income" and value not in [None, ""]:
            value = float(value)

        setattr(application, field, value)


def latest_document(db: Session, application_id: int, document_types: list[str]):
    return (
        db.query(ApplicationDocument)
        .filter(
            ApplicationDocument.application_id == application_id,
            ApplicationDocument.document_type.in_(document_types),
        )
        .order_by(ApplicationDocument.id.desc())
        .first()
    )


def find_file_path(document: ApplicationDocument | None) -> Path | None:
    if not document:
        return None

    possible_fields = [
        "file_path",
        "stored_file_path",
        "stored_file_name",
        "file_name",
        "original_file_name",
    ]

    for field in possible_fields:
        value = getattr(document, field, None)

        if not value:
            continue

        raw = Path(str(value))
        candidates = [
            raw,
            Path.cwd() / raw,
            Path("uploads") / raw.name,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        try:
            matches = list(Path("uploads").rglob(raw.name))
            if matches:
                return matches[-1]
        except Exception:
            pass

    return None


def draw_image(pdf: canvas.Canvas, image_path: Path, x: float, y: float, max_w: float, max_h: float) -> bool:
    try:
        image = ImageReader(str(image_path))
        image_w, image_h = image.getSize()

        scale = min(max_w / image_w, max_h / image_h)
        final_w = image_w * scale
        final_h = image_h * scale

        final_x = x + (max_w - final_w) / 2
        final_y = y + (max_h - final_h) / 2

        pdf.drawImage(
            image,
            final_x,
            final_y,
            width=final_w,
            height=final_h,
            preserveAspectRatio=True,
            mask="auto",
        )

        return True
    except Exception:
        return False


def create_fixed_live_pdf(application: Application, photo_path: Path | None) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"FIXED_LIVE_APPLICATION_{application.id}_{timestamp}.pdf"

    first_name = safe(application.first_name)
    last_name = safe(application.last_name)

    fields = [
        ("Application ID", safe(application.id)),
        ("Status", safe(application.status)),
        ("First Name", first_name),
        ("Last Name", last_name),
        ("Applicant Name", f"{first_name} {last_name}".strip()),
        ("Father Name", safe(application.father_name)),
        ("Mother Name", safe(application.mother_name)),
        ("Age", safe(application.age)),
        ("Phone", safe(application.phone)),
        ("Email", safe(application.email)),
        ("Address", safe(application.address)),
        ("Occupation", safe(application.occupation)),
        ("Monthly Income", money(application.monthly_income)),
    ]

    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(45, height - 45, "SmartLoan AI")

    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(45, height - 75, "FIXED LIVE Loan Application PDF")

    pdf.setFont("Helvetica", 9)
    pdf.drawString(45, height - 95, f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    pdf.drawString(45, height - 110, "This PDF is generated from the saved database values of this application.")

    photo_x = width - 190
    photo_y = height - 245
    photo_w = 140
    photo_h = 140

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(photo_x, photo_y + photo_h + 10, "Latest Uploaded Photo")
    pdf.rect(photo_x, photo_y, photo_w, photo_h)

    if photo_path and photo_path.exists() and photo_path.suffix.lower() in IMAGE_EXTENSIONS:
        if not draw_image(pdf, photo_path, photo_x + 6, photo_y + 6, photo_w - 12, photo_h - 12):
            pdf.setFont("Helvetica", 8)
            pdf.drawString(photo_x + 15, photo_y + 70, "Photo preview failed")
    else:
        pdf.setFont("Helvetica", 8)
        pdf.drawString(photo_x + 18, photo_y + 70, "No photo preview")

    y = height - 150
    table_x = 45
    label_w = 150
    value_w = width - 240
    row_h = 25

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(table_x, y + 20, "Latest Saved Application Information")

    for label, value in fields:
        if y < 70:
            pdf.showPage()
            y = height - 60

        pdf.rect(table_x, y - row_h + 5, label_w, row_h)
        pdf.rect(table_x + label_w, y - row_h + 5, value_w, row_h)

        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(table_x + 8, y - 12, label)

        pdf.setFont("Helvetica", 9)
        value_text = str(value)

        if len(value_text) > 70:
            pdf.drawString(table_x + label_w + 8, y - 12, value_text[:70])
            pdf.drawString(table_x + label_w + 8, y - 22, value_text[70:140])
        else:
            pdf.drawString(table_x + label_w + 8, y - 12, value_text)

        y -= row_h

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(45, 45, "Debug Note")
    pdf.setFont("Helvetica", 8)
    pdf.drawString(45, 30, "If this PDF has correct data but browser PDF does not, frontend button is calling old route.")

    pdf.save()

    return output_path


@router.patch("/applications/{application_id}/save-current-form")
def save_current_form(
    application_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if getattr(current_user, "role", None) != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    update_application_from_payload(application, payload)

    db.add(application)
    db.commit()
    db.refresh(application)

    return {
        "saved": True,
        "application_id": application.id,
        "first_name": application.first_name,
        "last_name": application.last_name,
        "father_name": application.father_name,
        "mother_name": application.mother_name,
        "age": application.age,
        "phone": application.phone,
        "email": application.email,
        "address": application.address,
        "occupation": application.occupation,
        "monthly_income": application.monthly_income,
        "status": application.status,
    }


@router.get("/applications/{application_id}/debug-state")
def debug_application_state(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if getattr(current_user, "role", None) != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    documents = (
        db.query(ApplicationDocument)
        .filter(ApplicationDocument.application_id == application_id)
        .order_by(ApplicationDocument.id.desc())
        .all()
    )

    document_data = []

    for document in documents:
        file_path = find_file_path(document)

        document_data.append({
            "id": document.id,
            "document_type": getattr(document, "document_type", None),
            "original_file_name": getattr(document, "original_file_name", None),
            "file_path": getattr(document, "file_path", None),
            "stored_file_path": getattr(document, "stored_file_path", None),
            "real_path_found": str(file_path) if file_path else None,
            "real_path_exists": bool(file_path and file_path.exists()),
        })

    return {
        "application": {
            "id": application.id,
            "first_name": application.first_name,
            "last_name": application.last_name,
            "father_name": application.father_name,
            "mother_name": application.mother_name,
            "age": application.age,
            "phone": application.phone,
            "email": application.email,
            "address": application.address,
            "occupation": application.occupation,
            "monthly_income": application.monthly_income,
            "status": application.status,
        },
        "documents": document_data,
    }


@router.post("/applications/{application_id}/download-fixed-live-pdf")
def download_fixed_live_pdf(
    application_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if getattr(current_user, "role", None) != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    update_application_from_payload(application, payload)

    db.add(application)
    db.commit()
    db.refresh(application)

    photo_document = latest_document(
        db,
        application.id,
        ["photo", "scan_photo", "profile_photo", "applicant_photo"],
    )

    photo_path = find_file_path(photo_document)

    pdf_path = create_fixed_live_pdf(application=application, photo_path=photo_path)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )
