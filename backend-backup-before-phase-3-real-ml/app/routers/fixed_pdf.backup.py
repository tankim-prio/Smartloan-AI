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

# --------------- helpers ---------------
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
    fields = [
        "first_name", "last_name", "father_name", "mother_name",
        "age", "phone", "email", "address", "occupation", "monthly_income",
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
    for attr in ["file_path", "stored_file_path", "stored_file_name", "file_name", "original_file_name"]:
        value = getattr(document, attr, None)
        if not value:
            continue
        raw = Path(str(value))
        candidates = [raw, Path.cwd() / raw, Path("uploads") / raw.name]
        for cand in candidates:
            if cand.exists():
                return cand
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
        iw, ih = image.getSize()
        scale = min(max_w / iw, max_h / ih)
        w, h = iw * scale, ih * scale
        fx = x + (max_w - w) / 2
        fy = y + (max_h - h) / 2
        pdf.drawImage(image, fx, fy, width=w, height=h, preserveAspectRatio=True, mask="auto")
        return True
    except Exception:
        return False

def make_image_pdf_page(title: str, image_path: Path) -> Path:
    with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    pdf = canvas.Canvas(str(tmp_path), pagesize=A4)
    width, height = A4
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(45, height - 45, title)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(45, height - 65, f"Included at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    x, y, bw, bh = 45, 70, width - 90, height - 150
    pdf.rect(x, y, bw, bh)
    if not draw_image(pdf, image_path, x + 10, y + 10, bw - 20, bh - 20):
        pdf.setFont("Helvetica", 12)
        pdf.drawString(70, height / 2, "Document preview not available.")
    pdf.save()
    return tmp_path

def append_pdf_or_image(writer: PdfWriter, title: str, file_path: Path | None):
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
        temp_pdf = make_image_pdf_page(title, file_path)
        try:
            reader = PdfReader(str(temp_pdf))
            for page in reader.pages:
                writer.add_page(page)
        finally:
            temp_pdf.unlink(missing_ok=True)

def create_main_pdf(application: Application, photo_path: Path | None) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"FIXED_MAIN_{application.id}_{timestamp}.pdf"
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

    px, py, pw, ph = width - 190, height - 245, 140, 140
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(px, py + ph + 10, "Latest Uploaded Photo")
    pdf.rect(px, py, pw, ph)
    if photo_path and photo_path.exists() and photo_path.suffix.lower() in IMAGE_EXTENSIONS:
        if not draw_image(pdf, photo_path, px + 6, py + 6, pw - 12, ph - 12):
            pdf.setFont("Helvetica", 8)
            pdf.drawString(px + 15, py + 70, "Photo preview failed")
    else:
        pdf.setFont("Helvetica", 8)
        pdf.drawString(px + 18, py + 70, "No photo preview")

    y = height - 150
    table_x = 45
    label_w, value_w = 150, width - 240
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
        text = str(value)
        if len(text) > 70:
            pdf.drawString(table_x + label_w + 8, y - 12, text[:70])
            pdf.drawString(table_x + label_w + 8, y - 22, text[70:140])
        else:
            pdf.drawString(table_x + label_w + 8, y - 12, text)
        y -= row_h

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(45, 45, "This PDF contains live data from your current application form.")
    pdf.save()
    return output_path

def create_full_fixed_pdf(db: Session, application: Application) -> Path:
    photo_doc = latest_document(db, application.id, ["photo", "scan_photo", "profile_photo", "applicant_photo"])
    identity_doc = latest_document(db, application.id, ["nid", "passport", "nid_or_passport", "identity_document"])
    income_doc = latest_document(db, application.id, ["salary_certificate", "tin_certificate", "salary_or_tin", "income_proof"])

    photo_path = find_file_path(photo_doc)
    identity_path = find_file_path(identity_doc)
    income_path = find_file_path(income_doc)

    main_pdf = create_main_pdf(application, photo_path)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_pdf = OUTPUT_DIR / f"FIXED_LIVE_APPLICATION_{application.id}_{timestamp}.pdf"
    writer = PdfWriter()

    reader = PdfReader(str(main_pdf))
    for page in reader.pages:
        writer.add_page(page)

    append_pdf_or_image(writer, "NID / Passport Document", identity_path)
    append_pdf_or_image(writer, "Salary Certificate / TIN Document", income_path)

    with open(final_pdf, "wb") as f:
        writer.write(f)

    main_pdf.unlink(missing_ok=True)
    return final_pdf

def save_generated_document(db: Session, application: Application, pdf_path: Path) -> ApplicationDocument:
    cols = set(ApplicationDocument.__table__.columns.keys())
    file_size = pdf_path.stat().st_size if pdf_path.exists() else 0
    data = {}
    if "application_id" in cols: data["application_id"] = application.id
    if "user_id" in cols: data["user_id"] = application.user_id
    if "document_type" in cols: data["document_type"] = "generated_pdf"
    if "original_file_name" in cols: data["original_file_name"] = pdf_path.name
    if "file_name" in cols: data["file_name"] = pdf_path.name
    if "stored_file_name" in cols: data["stored_file_name"] = pdf_path.name
    if "file_path" in cols: data["file_path"] = str(pdf_path)
    if "stored_file_path" in cols: data["stored_file_path"] = str(pdf_path)
    if "file_size" in cols: data["file_size"] = file_size
    if "size_bytes" in cols: data["size_bytes"] = file_size
    if "content_type" in cols: data["content_type"] = "application/pdf"
    if "mime_type" in cols: data["mime_type"] = "application/pdf"

    doc = ApplicationDocument(**data)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

def get_application_or_404(db: Session, application_id: int) -> Application:
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app

def check_permission(current_user, application: Application):
    if getattr(current_user, "role", None) != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

# --------------- endpoints ---------------
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
    return {"saved": True, "application_id": application.id, "first_name": application.first_name}

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
    return {"generated": True, "document_id": document.id, "file_name": pdf_path.name}

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
