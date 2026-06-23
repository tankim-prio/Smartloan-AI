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

    possible_values = []

    # Read common file/path fields first.
    for field in [
        "file_path",
        "stored_file_path",
        "stored_file_name",
        "file_name",
        "original_file_name",
        "path",
        "url",
    ]:
        try:
            value = getattr(document, field, None)
            if value:
                possible_values.append(str(value))
        except Exception:
            pass

    # Also inspect all SQLAlchemy columns that include file/path/name.
    try:
        for column in document.__table__.columns:
            column_name = column.name
            if any(key in column_name.lower() for key in ["file", "path", "name"]):
                value = getattr(document, column_name, None)
                if value:
                    possible_values.append(str(value))
    except Exception:
        pass

    # Unique values, keep order.
    cleaned_values = []
    for value in possible_values:
        value = value.strip().replace("\\\\", "/")
        if value and value not in cleaned_values:
            cleaned_values.append(value)

    for value in cleaned_values:
        raw = Path(value)

        candidates = [
            raw,
            Path.cwd() / raw,
            Path.cwd() / "uploads" / raw,
            Path.cwd() / "uploads" / raw.name,
            Path.cwd() / "uploads" / "applications" / str(getattr(document, "application_id", "")) / raw.name,
            Path("uploads") / raw,
            Path("uploads") / raw.name,
            Path("uploads") / "applications" / str(getattr(document, "application_id", "")) / raw.name,
        ]

        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate
            except Exception:
                pass

        try:
            matches = list(Path("uploads").rglob(raw.name))
            matches = [item for item in matches if item.is_file()]
            if matches:
                matches.sort(key=lambda item: item.stat().st_mtime, reverse=True)
                return matches[0]
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
    output_path = OUTPUT_DIR / f"LOAN_APPLICATION_MAIN_{application.id}_{timestamp}.pdf"

    first_name = safe(application.first_name)
    last_name = safe(application.last_name)
    applicant_name = f"{first_name} {last_name}".strip()

    fields = [
        ("Application ID", safe(application.id)),
        ("Status", safe(application.status)),
        ("First Name", first_name),
        ("Last Name", last_name),
        ("Applicant Name", applicant_name),
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

    margin = 42
    table_width = width - (margin * 2)

    # =========================
    # Header
    # =========================
    y = height - 48

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(margin, y, "SmartLoan AI")

    y -= 34
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawString(margin, y, "Loan Application PDF")

    y -= 24
    pdf.setFont("Helvetica", 9.5)
    pdf.drawString(
        margin,
        y,
        f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )

    y -= 16
    pdf.setFont("Helvetica", 9.5)
    pdf.drawString(
        margin,
        y,
        "This PDF is generated from the latest saved Apply page information.",
    )

    # =========================
    # Profile Picture section
    # =========================
    profile_section_top = y - 28
    photo_w = 120
    photo_h = 135

    photo_x = width - margin - photo_w
    photo_y = profile_section_top - photo_h - 18

    summary_x = margin
    summary_y = profile_section_top - 18

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(photo_x, profile_section_top, "Profile Picture")

    pdf.setStrokeColorRGB(0.1, 0.1, 0.1)
    pdf.setLineWidth(1)
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
            pdf.drawString(photo_x + 15, photo_y + 68, "Profile preview failed")
    else:
        pdf.setFont("Helvetica", 8)
        pdf.drawString(photo_x + 18, photo_y + 68, "No profile picture")

    # Left-side short summary to keep the top area balanced and professional
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(summary_x, summary_y, "Applicant Summary")

    pdf.setFont("Helvetica", 10)
    summary_y -= 22
    pdf.drawString(summary_x, summary_y, f"Applicant Name: {applicant_name or '-'}")

    summary_y -= 18
    pdf.drawString(summary_x, summary_y, f"Application ID: {safe(application.id)}")

    summary_y -= 18
    pdf.drawString(summary_x, summary_y, f"Status: {safe(application.status)}")

    summary_y -= 18
    pdf.drawString(summary_x, summary_y, f"Phone: {safe(application.phone)}")

    summary_y -= 18
    pdf.drawString(summary_x, summary_y, f"Email: {safe(application.email)}")

    # =========================
    # Full table under photo
    # =========================
    table_title_y = photo_y - 34

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin, table_title_y, "Applicant Information")

    table_top = table_title_y - 18
    row_h = 26
    label_w = 170
    value_w = table_width - label_w

    def draw_row(row_top: float, label: str, value: str, is_header: bool = False) -> float:
        row_bottom = row_top - row_h

        if is_header:
            pdf.setFillColorRGB(0.90, 0.94, 1.0)
            pdf.rect(margin, row_bottom, table_width, row_h, fill=1, stroke=0)
            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont("Helvetica-Bold", 9.5)
        else:
            pdf.setFillColorRGB(1, 1, 1)
            pdf.rect(margin, row_bottom, table_width, row_h, fill=1, stroke=0)
            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont("Helvetica-Bold", 9.5)

        pdf.setStrokeColorRGB(0, 0, 0)
        pdf.setLineWidth(0.8)

        pdf.rect(margin, row_bottom, label_w, row_h)
        pdf.rect(margin + label_w, row_bottom, value_w, row_h)

        pdf.drawString(margin + 8, row_bottom + 8, label)

        if is_header:
            pdf.setFont("Helvetica-Bold", 9.5)
        else:
            pdf.setFont("Helvetica", 9.5)

        value_text = str(value)

        if len(value_text) <= 78:
            pdf.drawString(margin + label_w + 8, row_bottom + 8, value_text)
        else:
            pdf.drawString(margin + label_w + 8, row_bottom + 13, value_text[:78])
            pdf.drawString(margin + label_w + 8, row_bottom + 3, value_text[78:156])

        return row_bottom

    current_y = table_top

    current_y = draw_row(current_y, "Field", "Value", is_header=True)

    for label, value in fields:
        if current_y - row_h < 60:
            pdf.showPage()
            current_y = height - 60

            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(margin, current_y, "Applicant Information Continued")
            current_y -= 18

            current_y = draw_row(current_y, "Field", "Value", is_header=True)

        current_y = draw_row(current_y, label, value)

    # =========================
    # Professional footer
    # =========================
    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.35, 0.35, 0.35)
    pdf.drawString(margin, 32, "Generated by SmartLoan AI")
    pdf.drawRightString(width - margin, 32, "Loan Application PDF")

    pdf.save()

    return output_path





def create_missing_document_page(title: str, message: str) -> Path:
    with NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
        temp_path = Path(temp.name)

    pdf = canvas.Canvas(str(temp_path), pagesize=A4)
    width, height = A4

    margin = 45

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(margin, height - 55, "SmartLoan AI")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, height - 90, title)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, height - 120, message)

    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(1)
    pdf.rect(margin, height - 260, width - (margin * 2), 100)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin + 18, height - 180, "Document Status")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin + 18, height - 205, "No valid document file was found for this section.")

    pdf.setFont("Helvetica", 8)
    pdf.drawString(margin, 35, "Generated by SmartLoan AI")
    pdf.drawRightString(width - margin, 35, "Loan Application PDF")

    pdf.save()

    return temp_path


def get_document_text_for_matching(document: ApplicationDocument | None) -> str:
    if not document:
        return ""

    values = []

    try:
        for column in document.__table__.columns:
            value = getattr(document, column.name, None)
            if value:
                values.append(str(value))
    except Exception:
        pass

    return " ".join(values).lower()


def same_real_file(path_one: Path | None, path_two: Path | None) -> bool:
    if not path_one or not path_two:
        return False

    try:
        return path_one.resolve() == path_two.resolve()
    except Exception:
        return str(path_one) == str(path_two)


def is_pdf_or_image(path: Path | None) -> bool:
    if not path or not path.exists():
        return False

    return path.suffix.lower() in [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".bmp"]


def has_any(text: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def is_generated_or_final_loan_doc(document: ApplicationDocument | None) -> bool:
    text = get_document_text_for_matching(document)

    return has_any(
        text,
        [
            "generated_pdf",
            "loan_application",
            "loan application pdf",
            "loan_application_pdf",
            "fixed_live_application",
            "loan_application_main",
        ],
    )


def is_photo_like_document(document: ApplicationDocument | None) -> bool:
    text = get_document_text_for_matching(document)

    return has_any(
        text,
        [
            "photo",
            "scan_photo",
            "profile_photo",
            "applicant_photo",
            "profile picture",
            "picture",
            "image",
            "scan",
            "applicant",
        ],
    )


def is_income_like_document(document: ApplicationDocument | None) -> bool:
    text = get_document_text_for_matching(document)

    return has_any(
        text,
        [
            "salary_certificate",
            "tin_certificate",
            "salary",
            "tin",
            "income",
            "payroll",
            "employment",
        ],
    )


def is_identity_like_document(document: ApplicationDocument | None) -> bool:
    text = get_document_text_for_matching(document)

    return has_any(
        text,
        [
            "nid",
            "passport",
            "identity",
            "identity_document",
            "identityproof",
            "identity_proof",
            "national_id",
            "national id",
            "id_document",
            "id document",
            "id proof",
        ],
    )


def get_all_documents_latest_first(db: Session, application_id: int):
    return (
        db.query(ApplicationDocument)
        .filter(ApplicationDocument.application_id == application_id)
        .order_by(ApplicationDocument.id.desc())
        .all()
    )


def choose_latest_photo_document(db: Session, application_id: int):
    documents = get_all_documents_latest_first(db, application_id)

    # First: explicit photo/scan documents.
    for document in documents:
        if is_generated_or_final_loan_doc(document):
            continue

        file_path = find_file_path(document)

        if not is_pdf_or_image(file_path):
            continue

        if is_photo_like_document(document):
            return document, file_path

    # Second: latest image that is not income/identity/generated.
    for document in documents:
        if is_generated_or_final_loan_doc(document):
            continue

        if is_income_like_document(document) or is_identity_like_document(document):
            continue

        file_path = find_file_path(document)

        if file_path and file_path.exists() and file_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
            return document, file_path

    return None, None


def choose_latest_income_document(db: Session, application_id: int):
    documents = get_all_documents_latest_first(db, application_id)

    for document in documents:
        if is_generated_or_final_loan_doc(document):
            continue

        file_path = find_file_path(document)

        if not is_pdf_or_image(file_path):
            continue

        if is_income_like_document(document):
            return document, file_path

    return None, None


def choose_latest_identity_document(
    db: Session,
    application_id: int,
    excluded_paths: list[Path | None],
):
    documents = get_all_documents_latest_first(db, application_id)

    # First: explicit NID / Passport / identity documents.
    for document in documents:
        if is_generated_or_final_loan_doc(document):
            continue

        if is_income_like_document(document):
            continue

        file_path = find_file_path(document)

        if not is_pdf_or_image(file_path):
            continue

        if any(same_real_file(file_path, excluded) for excluded in excluded_paths):
            continue

        if is_identity_like_document(document):
            return document, file_path

    # Second: any latest PDF/image not used by photo/income and not generated.
    # This catches cases where backend stored wrong document_type but file is actually NID/passport.
    for document in documents:
        if is_generated_or_final_loan_doc(document):
            continue

        if is_income_like_document(document):
            continue

        file_path = find_file_path(document)

        if not is_pdf_or_image(file_path):
            continue

        if any(same_real_file(file_path, excluded) for excluded in excluded_paths):
            continue

        return document, file_path

    return None, None


def add_pdf_or_placeholder(
    writer: PdfWriter,
    section_title: str,
    file_path: Path | None,
    missing_message: str,
):
    if file_path and file_path.exists():
        append_pdf_or_image(writer, section_title, file_path)
        return

    missing_page = create_missing_document_page(section_title, missing_message)

    try:
        missing_reader = PdfReader(str(missing_page))

        for page in missing_reader.pages:
            writer.add_page(page)
    finally:
        try:
            missing_page.unlink(missing_ok=True)
        except Exception:
            pass


def create_full_fixed_pdf(db: Session, application: Application) -> Path:
    photo_document, photo_path = choose_latest_photo_document(db, application.id)
    income_document, income_path = choose_latest_income_document(db, application.id)

    identity_document, identity_path = choose_latest_identity_document(
        db=db,
        application_id=application.id,
        excluded_paths=[photo_path, income_path],
    )

    # Absolute safety: page 3 must not reuse profile photo or salary certificate.
    if same_real_file(identity_path, income_path) or same_real_file(identity_path, photo_path):
        identity_document = None
        identity_path = None

    main_pdf = create_main_pdf(application, photo_path)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_pdf = OUTPUT_DIR / f"LOAN_APPLICATION_PDF_{application.id}_{timestamp}.pdf"

    writer = PdfWriter()

    # Page 1: Loan Application
    main_reader = PdfReader(str(main_pdf))

    for page in main_reader.pages:
        writer.add_page(page)

    # Page 2: Salary Certificate / TIN Certificate
    add_pdf_or_placeholder(
        writer=writer,
        section_title="Salary Certificate / TIN Certificate",
        file_path=income_path,
        missing_message="Salary Certificate or TIN Certificate was not uploaded for this application.",
    )

    # Page 3: NID / Passport
    add_pdf_or_placeholder(
        writer=writer,
        section_title="NID / Passport Document",
        file_path=identity_path,
        missing_message="NID or Passport document was not uploaded for this application.",
    )

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
