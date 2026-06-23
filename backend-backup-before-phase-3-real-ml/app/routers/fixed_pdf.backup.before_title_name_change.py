from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.application import Application
from app.models.application_document import ApplicationDocument


router = APIRouter(prefix="/fixed-pdf", tags=["Fixed Live PDF"])

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


def update_application_from_payload(application: Application, payload: dict) -> None:
    fields = [
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

    for field in fields:
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


def draw_image(
    pdf: canvas.Canvas,
    image_path: Path,
    x: float,
    y: float,
    max_w: float,
    max_h: float,
) -> bool:
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


def create_image_pdf_page(title: str, image_path: Path) -> Path:
    with NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
        temp_path = Path(temp.name)

    pdf = canvas.Canvas(str(temp_path), pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(45, height - 45, title)

    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        45,
        height - 65,
        f"Included at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )

    x = 45
    y = 70
    box_w = width - 90
    box_h = height - 150

    pdf.rect(x, y, box_w, box_h)

    ok = draw_image(pdf, image_path, x + 10, y + 10, box_w - 20, box_h - 20)

    if not ok:
        pdf.setFont("Helvetica", 12)
        pdf.drawString(70, height / 2, "Document preview not available.")

    pdf.save()

    return temp_path


def append_pdf_or_image(writer: PdfWriter, title: str, file_path: Path | None) -> None:
    if not file_path or not file_path.exists():
        return

    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        try:
            reader = PdfReader(str(file_path))
            for page in reader.pages:
                writer.add_page(page)
        except Exception:
            pass

        return

    if suffix in IMAGE_EXTENSIONS:
        temp_pdf = create_image_pdf_page(title, file_path)

        try:
            reader = PdfReader(str(temp_pdf))
            for page in reader.pages:
                writer.add_page(page)
        finally:
            try:
                temp_pdf.unlink(missing_ok=True)
            except Exception:
                pass


def create_main_pdf(application: Application, photo_path: Path | None) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"FIXED_MAIN_APPLICATION_{application.id}_{timestamp}.pdf"

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
    pdf.drawString(
        45,
        height - 95,
        f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )
    pdf.drawString(
        45,
        height - 110,
        "This PDF is generated from the latest saved Apply page information.",
    )

    photo_x = width - 190
    photo_y = height - 245
    photo_w = 140
    photo_h = 140

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(photo_x, photo_y + photo_h + 10, "Latest Uploaded Photo")
    pdf.rect(photo_x, photo_y, photo_w, photo_h)

    if photo_path and photo_path.exists() and photo_path.suffix.lower() in IMAGE_EXTENSIONS:
        image_ok = draw_image(
            pdf,
            photo_path,
            photo_x + 6,
            photo_y + 6,
            photo_w - 12,
            photo_h - 12,
        )

        if not image_ok:
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
    pdf.drawString(
        45,
        30,
        "If this file shows current values, backend and PDF generation are working correctly.",
    )

    pdf.save()

    return output_path


def create_full_fixed_pdf(db: Session, application: Application) -> Path:
    photo_document = latest_document(
        db,
        application.id,
        ["photo", "scan_photo", "profile_photo", "applicant_photo"],
    )

    identity_document = latest_document(
        db,
        application.id,
        ["nid", "passport", "nid_or_passport", "identity_document"],
    )

    income_document = latest_document(
        db,
        application.id,
        ["salary_certificate", "tin_certificate", "salary_or_tin", "income_proof"],
    )

    photo_path = find_file_path(photo_document)
    identity_path = find_file_path(identity_document)
    income_path = find_file_path(income_document)

    main_pdf = create_main_pdf(application, photo_path)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_pdf = OUTPUT_DIR / f"FIXED_LIVE_APPLICATION_{application.id}_{timestamp}.pdf"

    writer = PdfWriter()

    reader = PdfReader(str(main_pdf))
    for page in reader.pages:
        writer.add_page(page)

    append_pdf_or_image(writer, "NID / Passport Document", identity_path)
    append_pdf_or_image(writer, "Salary Certificate / TIN Document", income_path)

    with open(final_pdf, "wb") as file:
        writer.write(file)

    try:
        main_pdf.unlink(missing_ok=True)
    except Exception:
        pass

    return final_pdf


def save_generated_document(
    db: Session,
    application: Application,
    pdf_path: Path,
) -> ApplicationDocument:
    columns = set(ApplicationDocument.__table__.columns.keys())

    try:
        file_size = pdf_path.stat().st_size
    except Exception:
        file_size = 0

    data = {}

    if "application_id" in columns:
        data["application_id"] = application.id

    if "user_id" in columns:
        data["user_id"] = application.user_id

    if "document_type" in columns:
        data["document_type"] = "generated_pdf"

    if "original_file_name" in columns:
        data["original_file_name"] = pdf_path.name

    if "file_name" in columns:
        data["file_name"] = pdf_path.name

    if "stored_file_name" in columns:
        data["stored_file_name"] = pdf_path.name

    if "file_path" in columns:
        data["file_path"] = str(pdf_path)

    if "stored_file_path" in columns:
        data["stored_file_path"] = str(pdf_path)

    if "file_size" in columns:
        data["file_size"] = file_size

    if "size_bytes" in columns:
        data["size_bytes"] = file_size

    if "content_type" in columns:
        data["content_type"] = "application/pdf"

    if "mime_type" in columns:
        data["mime_type"] = "application/pdf"

    document = ApplicationDocument(**data)

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return application


def check_permission(current_user, application: Application) -> None:
    if getattr(current_user, "role", None) != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")


@router.patch("/applications/{application_id}/save-current-form")
def save_current_form(
    application_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_permission(current_user, application)

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


@router.post("/applications/{application_id}/generate")
def generate_fixed_pdf(
    application_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_permission(current_user, application)

    update_application_from_payload(application, payload)

    db.add(application)
    db.commit()
    db.refresh(application)

    pdf_path = create_full_fixed_pdf(db, application)
    document = save_generated_document(db, application, pdf_path)

    return document


@router.post("/applications/{application_id}/download")
def download_fixed_pdf(
    application_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_permission(current_user, application)

    update_application_from_payload(application, payload)

    db.add(application)
    db.commit()
    db.refresh(application)

    pdf_path = create_full_fixed_pdf(db, application)
    save_generated_document(db, application, pdf_path)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )


@router.get("/applications/{application_id}/debug-state")
def debug_state(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_permission(current_user, application)

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
