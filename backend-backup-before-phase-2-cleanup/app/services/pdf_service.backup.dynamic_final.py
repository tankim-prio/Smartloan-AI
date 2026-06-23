from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.models.application_document import ApplicationDocument


UPLOAD_DIR = Path("uploads")
GENERATED_DIR = UPLOAD_DIR / "generated_pdfs"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _safe(value):
    if value is None or value == "":
        return "-"
    return str(value)


def _money(value):
    if value is None:
        return "-"
    try:
        return f"BDT {float(value):,.2f}"
    except Exception:
        return str(value)


def _file_path(document):
    if not document:
        return None

    possible_fields = [
        "file_path",
        "stored_file_path",
        "path",
        "document_path",
    ]

    for field in possible_fields:
        value = getattr(document, field, None)
        if value:
            path = Path(str(value))
            if path.exists():
                return path

            relative_path = Path.cwd() / path
            if relative_path.exists():
                return relative_path

    return None


def _latest_document(db, application_id, document_types):
    return (
        db.query(ApplicationDocument)
        .filter(
            ApplicationDocument.application_id == application_id,
            ApplicationDocument.document_type.in_(document_types),
        )
        .order_by(ApplicationDocument.id.desc())
        .first()
    )


def _draw_image_fit(pdf_canvas, image_path, x, y, max_width, max_height):
    try:
        image = ImageReader(str(image_path))
        image_width, image_height = image.getSize()

        width_ratio = max_width / image_width
        height_ratio = max_height / image_height
        scale = min(width_ratio, height_ratio)

        final_width = image_width * scale
        final_height = image_height * scale

        centered_x = x + (max_width - final_width) / 2
        centered_y = y + (max_height - final_height) / 2

        pdf_canvas.drawImage(
            image,
            centered_x,
            centered_y,
            width=final_width,
            height=final_height,
            preserveAspectRatio=True,
            mask="auto",
        )

        return True
    except Exception:
        return False


def _create_application_info_pdf(application, photo_path, output_path):
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawString(45, height - 50, "SmartLoan AI - Loan Application")

    c.setFont("Helvetica", 9)
    c.drawString(45, height - 68, f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(45, height - 82, f"Application ID: {_safe(application.id)}")

    # photo box
    photo_x = width - 185
    photo_y = height - 205
    photo_w = 135
    photo_h = 135

    c.setFont("Helvetica-Bold", 10)
    c.drawString(photo_x, photo_y + photo_h + 10, "Applicant Photo / Scan")

    c.rect(photo_x, photo_y, photo_w, photo_h)

    if photo_path:
        ok = _draw_image_fit(c, photo_path, photo_x + 5, photo_y + 5, photo_w - 10, photo_h - 10)
        if not ok:
            c.setFont("Helvetica", 9)
            c.drawString(photo_x + 15, photo_y + 65, "Photo preview")
            c.drawString(photo_x + 15, photo_y + 50, "not available")
    else:
        c.setFont("Helvetica", 9)
        c.drawString(photo_x + 15, photo_y + 65, "No photo uploaded")

    c.setFont("Helvetica-Bold", 13)
    c.drawString(45, height - 120, "Applicant Information")

    fields = [
        ("First Name", _safe(getattr(application, "first_name", None))),
        ("Last Name", _safe(getattr(application, "last_name", None))),
        ("Father Name", _safe(getattr(application, "father_name", None))),
        ("Mother Name", _safe(getattr(application, "mother_name", None))),
        ("Age", _safe(getattr(application, "age", None))),
        ("Phone", _safe(getattr(application, "phone", None))),
        ("Email", _safe(getattr(application, "email", None))),
        ("Address", _safe(getattr(application, "address", None))),
        ("Occupation", _safe(getattr(application, "occupation", None))),
        ("Monthly Income", _money(getattr(application, "monthly_income", None))),
        ("Application Status", _safe(getattr(application, "status", None))),
        ("Created At", _safe(getattr(application, "created_at", None))),
        ("Updated At", _safe(getattr(application, "updated_at", None))),
    ]

    y = height - 150
    label_x = 55
    value_x = 190

    for label, value in fields:
        if y < 80:
            c.showPage()
            y = height - 60

        c.setFont("Helvetica-Bold", 10)
        c.drawString(label_x, y, f"{label}:")
        c.setFont("Helvetica", 10)

        value_text = str(value)
        max_len = 70

        if len(value_text) > max_len:
            c.drawString(value_x, y, value_text[:max_len])
            y -= 14
            c.drawString(value_x, y, value_text[max_len:max_len * 2])
        else:
            c.drawString(value_x, y, value_text)

        y -= 24

    c.setFont("Helvetica-Bold", 12)
    c.drawString(45, 55, "Declaration")
    c.setFont("Helvetica", 9)
    c.drawString(
        45,
        40,
        "This PDF was generated dynamically from the latest submitted application data and uploaded documents.",
    )

    c.save()


def _create_image_page_pdf(title, image_path):
    with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    c = canvas.Canvas(str(temp_path), pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(45, height - 50, title)

    c.setFont("Helvetica", 9)
    c.drawString(45, height - 68, f"Included at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    box_x = 45
    box_y = 70
    box_w = width - 90
    box_h = height - 155

    c.rect(box_x, box_y, box_w, box_h)

    ok = _draw_image_fit(c, image_path, box_x + 10, box_y + 10, box_w - 20, box_h - 20)

    if not ok:
        c.setFont("Helvetica", 12)
        c.drawString(70, height / 2, "Document preview not available.")

    c.save()

    return temp_path


def _append_pdf_or_image(writer, title, file_path):
    if not file_path or not file_path.exists():
        return

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        try:
            reader = PdfReader(str(file_path))
            for page in reader.pages:
                writer.add_page(page)
            return
        except Exception:
            return

    if extension in IMAGE_EXTENSIONS:
        temp_pdf = _create_image_page_pdf(title, file_path)

        try:
            reader = PdfReader(str(temp_pdf))
            for page in reader.pages:
                writer.add_page(page)
        finally:
            try:
                temp_pdf.unlink(missing_ok=True)
            except Exception:
                pass


def create_dynamic_application_pdf(db, application):
    """
    Creates a fresh PDF every time using:
    - latest Step 1 information
    - latest Step 2 occupation/monthly income
    - latest uploaded scan/photo
    - latest uploaded NID/Passport
    - latest uploaded Salary/TIN certificate
    """

    db.refresh(application)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_pdf = GENERATED_DIR / f"application_{application.id}_base_{timestamp}.pdf"
    final_pdf = GENERATED_DIR / f"application_{application.id}_dynamic_{timestamp}.pdf"

    photo_doc = _latest_document(
        db,
        application.id,
        ["photo", "scan_photo", "profile_photo", "applicant_photo"],
    )

    identity_doc = _latest_document(
        db,
        application.id,
        ["nid", "passport", "nid_or_passport", "identity_document"],
    )

    income_doc = _latest_document(
        db,
        application.id,
        ["salary_certificate", "tin_certificate", "salary_or_tin", "income_proof"],
    )

    photo_path = _file_path(photo_doc)
    identity_path = _file_path(identity_doc)
    income_path = _file_path(income_doc)

    _create_application_info_pdf(application, photo_path, base_pdf)

    writer = PdfWriter()

    base_reader = PdfReader(str(base_pdf))
    for page in base_reader.pages:
        writer.add_page(page)

    _append_pdf_or_image(writer, "NID / Passport Document", identity_path)
    _append_pdf_or_image(writer, "Salary Certificate / TIN Document", income_path)

    with open(final_pdf, "wb") as output:
        writer.write(output)

    try:
        base_pdf.unlink(missing_ok=True)
    except Exception:
        pass

    return str(final_pdf)


# Backward-compatible function names
def generate_application_pdf(db, application):
    return create_dynamic_application_pdf(db, application)


def create_application_pdf(db, application):
    return create_dynamic_application_pdf(db, application)
