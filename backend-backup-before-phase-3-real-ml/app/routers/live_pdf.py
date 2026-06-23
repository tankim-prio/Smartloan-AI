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


router = APIRouter(prefix="/live-pdf", tags=["Live PDF"])

OUTPUT_DIR = Path("uploads") / "live_generated_pdfs"
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


def find_document_path(document: ApplicationDocument | None) -> Path | None:
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

        value_path = Path(str(value))

        candidates = [
            value_path,
            Path.cwd() / value_path,
            Path("uploads") / value_path.name,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        try:
            matches = list(Path("uploads").rglob(value_path.name))
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


def write_pdf(application: Application, payload: dict, photo_path: Path | None) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"live_application_{application.id}_{timestamp}.pdf"

    first_name = safe(payload.get("first_name", application.first_name))
    last_name = safe(payload.get("last_name", application.last_name))

    fields = [
        ("Application ID", safe(application.id)),
        ("Status", safe(application.status)),
        ("First Name", first_name),
        ("Last Name", last_name),
        ("Applicant Name", f"{first_name} {last_name}".strip()),
        ("Father Name", safe(payload.get("father_name", application.father_name))),
        ("Mother Name", safe(payload.get("mother_name", application.mother_name))),
        ("Age", safe(payload.get("age", application.age))),
        ("Phone", safe(payload.get("phone", application.phone))),
        ("Email", safe(payload.get("email", application.email))),
        ("Address", safe(payload.get("address", application.address))),
        ("Occupation", safe(payload.get("occupation", application.occupation))),
        ("Monthly Income", money(payload.get("monthly_income", application.monthly_income))),
    ]

    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(45, height - 45, "SmartLoan AI")

    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(45, height - 75, "LIVE Generated Loan Application PDF")

    pdf.setFont("Helvetica", 9)
    pdf.drawString(45, height - 95, f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    pdf.drawString(45, height - 110, "This PDF uses the latest values sent from the Apply page.")

    photo_x = width - 190
    photo_y = height - 245
    photo_w = 140
    photo_h = 140

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(photo_x, photo_y + photo_h + 10, "Uploaded Scan / Photo")
    pdf.rect(photo_x, photo_y, photo_w, photo_h)

    if photo_path and photo_path.exists() and photo_path.suffix.lower() in IMAGE_EXTENSIONS:
        if not draw_image(pdf, photo_path, photo_x + 6, photo_y + 6, photo_w - 12, photo_h - 12):
            pdf.setFont("Helvetica", 8)
            pdf.drawString(photo_x + 15, photo_y + 70, "Photo preview failed")
    else:
        pdf.setFont("Helvetica", 8)
        pdf.drawString(photo_x + 18, photo_y + 70, "No photo preview")

    y = height - 150
    label_w = 150
    value_w = width - 240
    row_h = 25
    table_x = 45

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(table_x, y + 20, "Latest Application Information")

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
    pdf.drawString(45, 45, "Important")
    pdf.setFont("Helvetica", 8)
    pdf.drawString(45, 30, "If this PDF does not show your newest form data, the frontend button is not calling /live-pdf/{id}/download.")

    pdf.save()

    return output_path


@router.post("/{application_id}/download")
def create_and_download_live_pdf(
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

    db.add(application)
    db.commit()
    db.refresh(application)

    photo_doc = latest_document(
        db,
        application.id,
        ["photo", "scan_photo", "profile_photo", "applicant_photo"],
    )

    photo_path = find_document_path(photo_doc)

    pdf_path = write_pdf(application=application, payload=payload, photo_path=photo_path)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"generated_application_{application.id}_LIVE.pdf",
    )
