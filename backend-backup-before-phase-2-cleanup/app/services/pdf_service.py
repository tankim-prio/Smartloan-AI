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


def safe_value(value):
    if value is None or value == "":
        return "-"
    return str(value)


def money_value(value):
    if value is None:
        return "-"

    try:
        return f"BDT {float(value):,.2f}"
    except Exception:
        return str(value)


def get_document_file_path(document):
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

        if not value:
            continue

        file_path = Path(str(value))

        if file_path.exists():
            return file_path

        local_path = Path.cwd() / file_path

        if local_path.exists():
            return local_path

    return None


def get_latest_document(db, application_id, document_types):
    return (
        db.query(ApplicationDocument)
        .filter(
            ApplicationDocument.application_id == application_id,
            ApplicationDocument.document_type.in_(document_types),
        )
        .order_by(ApplicationDocument.id.desc())
        .first()
    )


def draw_image_fit(pdf, image_path, x, y, max_width, max_height):
    try:
        image = ImageReader(str(image_path))
        image_width, image_height = image.getSize()

        scale = min(max_width / image_width, max_height / image_height)

        final_width = image_width * scale
        final_height = image_height * scale

        final_x = x + (max_width - final_width) / 2
        final_y = y + (max_height - final_height) / 2

        pdf.drawImage(
            image,
            final_x,
            final_y,
            width=final_width,
            height=final_height,
            preserveAspectRatio=True,
            mask="auto",
        )

        return True
    except Exception:
        return False


def create_main_application_page(application, photo_path, output_path):
    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(45, height - 45, "SmartLoan AI - Loan Application")

    pdf.setFont("Helvetica", 9)
    pdf.drawString(45, height - 65, f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    pdf.drawString(45, height - 80, f"Application ID: {safe_value(application.id)}")

    photo_x = width - 190
    photo_y = height - 220
    photo_w = 140
    photo_h = 140

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(photo_x, photo_y + photo_h + 10, "Uploaded Scan / Photo")
    pdf.rect(photo_x, photo_y, photo_w, photo_h)

    if photo_path and Path(photo_path).exists():
        image_ok = draw_image_fit(
            pdf,
            photo_path,
            photo_x + 6,
            photo_y + 6,
            photo_w - 12,
            photo_h - 12,
        )

        if not image_ok:
            pdf.setFont("Helvetica", 9)
            pdf.drawString(photo_x + 18, photo_y + 70, "Image preview")
            pdf.drawString(photo_x + 18, photo_y + 55, "not available")
    else:
        pdf.setFont("Helvetica", 9)
        pdf.drawString(photo_x + 18, photo_y + 70, "No photo uploaded")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(45, height - 120, "Latest Applicant Information")

    fields = [
        ("First Name", safe_value(getattr(application, "first_name", None))),
        ("Last Name", safe_value(getattr(application, "last_name", None))),
        ("Father Name", safe_value(getattr(application, "father_name", None))),
        ("Mother Name", safe_value(getattr(application, "mother_name", None))),
        ("Age", safe_value(getattr(application, "age", None))),
        ("Phone", safe_value(getattr(application, "phone", None))),
        ("Email", safe_value(getattr(application, "email", None))),
        ("Address", safe_value(getattr(application, "address", None))),
        ("Occupation", safe_value(getattr(application, "occupation", None))),
        ("Monthly Income", money_value(getattr(application, "monthly_income", None))),
        ("Application Status", safe_value(getattr(application, "status", None))),
        ("Created At", safe_value(getattr(application, "created_at", None))),
        ("Updated At", safe_value(getattr(application, "updated_at", None))),
    ]

    y = height - 155

    for label, value in fields:
        if y < 70:
            pdf.showPage()
            y = height - 60

        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(55, y, f"{label}:")

        pdf.setFont("Helvetica", 10)
        value_text = str(value)

        if len(value_text) > 62:
            pdf.drawString(190, y, value_text[:62])
            y -= 14
            pdf.drawString(190, y, value_text[62:124])
        else:
            pdf.drawString(190, y, value_text)

        y -= 24

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(45, 50, "Dynamic PDF Note")

    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        45,
        35,
        "This PDF is generated from the latest submitted Step 1, Step 2 and uploaded scan/photo data.",
    )

    pdf.save()


def create_image_pdf_page(title, image_path):
    with NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
        temp_pdf_path = Path(temp.name)

    pdf = canvas.Canvas(str(temp_pdf_path), pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(45, height - 45, title)

    pdf.setFont("Helvetica", 9)
    pdf.drawString(45, height - 65, f"Included at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    x = 45
    y = 70
    box_width = width - 90
    box_height = height - 150

    pdf.rect(x, y, box_width, box_height)

    ok = draw_image_fit(pdf, image_path, x + 10, y + 10, box_width - 20, box_height - 20)

    if not ok:
        pdf.setFont("Helvetica", 12)
        pdf.drawString(70, height / 2, "Document preview not available.")

    pdf.save()

    return temp_pdf_path


def append_pdf_or_image(writer, title, file_path):
    if not file_path:
        return

    file_path = Path(file_path)

    if not file_path.exists():
        return

    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        try:
            reader = PdfReader(str(file_path))

            for page in reader.pages:
                writer.add_page(page)

            return
        except Exception:
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


def create_dynamic_application_pdf(db, application):
    db.refresh(application)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    base_pdf = GENERATED_DIR / f"application_{application.id}_base_{timestamp}.pdf"
    final_pdf = GENERATED_DIR / f"application_{application.id}_dynamic_{timestamp}.pdf"

    photo_doc = get_latest_document(
        db,
        application.id,
        ["photo", "scan_photo", "profile_photo", "applicant_photo"],
    )

    identity_doc = get_latest_document(
        db,
        application.id,
        ["nid", "passport", "nid_or_passport", "identity_document"],
    )

    income_doc = get_latest_document(
        db,
        application.id,
        ["salary_certificate", "tin_certificate", "salary_or_tin", "income_proof"],
    )

    photo_path = get_document_file_path(photo_doc)
    identity_path = get_document_file_path(identity_doc)
    income_path = get_document_file_path(income_doc)

    create_main_application_page(application, photo_path, base_pdf)

    writer = PdfWriter()

    main_reader = PdfReader(str(base_pdf))

    for page in main_reader.pages:
        writer.add_page(page)

    append_pdf_or_image(writer, "NID / Passport Document", identity_path)
    append_pdf_or_image(writer, "Salary Certificate / TIN Document", income_path)

    with open(final_pdf, "wb") as output_file:
        writer.write(output_file)

    try:
        base_pdf.unlink(missing_ok=True)
    except Exception:
        pass

    return str(final_pdf)


def generate_application_pdf(db, application):
    return create_dynamic_application_pdf(db, application)


def create_application_pdf(db, application):
    return create_dynamic_application_pdf(db, application)
