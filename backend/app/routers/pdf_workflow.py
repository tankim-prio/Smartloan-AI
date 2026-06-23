from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


router = APIRouter(tags=["PDF Workflow"])

BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BASE_DIR / "storage"
PDF_DIR = STORAGE_DIR / "generated_pdfs"
UPLOAD_DIR = STORAGE_DIR / "loan_uploads"

PDF_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def pick(data: Dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = data.get(key)
        if value not in [None, ""]:
            return value
    return default


def normalize_application(application_id: int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = payload or {}

    first_name = str(pick(payload, "first_name", "firstName", default="")).strip()
    last_name = str(pick(payload, "last_name", "lastName", default="")).strip()

    applicant_name = str(
        pick(
            payload,
            "applicant_name",
            "applicantName",
            "name",
            default=f"{first_name} {last_name}".strip() or "Not provided",
        )
    ).strip()

    monthly_income = pick(payload, "monthly_income", "monthlyIncome", "income", default=0)
    age = pick(payload, "age", default="")

    try:
        monthly_income = float(str(monthly_income).replace(",", "").strip() or 0)
    except Exception:
        monthly_income = 0

    try:
        age = int(float(str(age).strip()))
    except Exception:
        age = ""

    return {
        "application_id": application_id,
        "status": str(pick(payload, "status", default="draft")),
        "first_name": first_name,
        "last_name": last_name,
        "applicant_name": applicant_name,
        "father_name": str(pick(payload, "father_name", "fatherName", default="Not provided")),
        "mother_name": str(pick(payload, "mother_name", "motherName", default="Not provided")),
        "age": age,
        "phone": str(pick(payload, "phone", "mobile", default="Not provided")),
        "email": str(pick(payload, "email", default="Not provided")),
        "address": str(pick(payload, "address", default="Not provided")),
        "occupation": str(pick(payload, "occupation", "job", default="Not provided")),
        "monthly_income": monthly_income,
        "photo_document": str(pick(payload, "photo_document", "photoDocument", "photo_file", "photoFile", default="No photo uploaded")),
        "income_document": str(pick(payload, "income_document", "incomeDocument", "salary_document", "salaryDocument", default="No income document uploaded")),
        "identity_document": str(pick(payload, "identity_document", "identityDocument", "nid_document", "nidDocument", default="No identity document uploaded")),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def application_pdf_path(application_id: int) -> Path:
    return PDF_DIR / f"generated_application_{application_id}.pdf"


def uploaded_pdf_path(application_id: int) -> Path:
    return UPLOAD_DIR / str(application_id) / "loan_application.pdf"


def safe(value: Any) -> str:
    return escape(str(value))


def create_application_pdf(application_id: int, payload: Optional[Dict[str, Any]] = None) -> Path:
    data = normalize_application(application_id, payload)
    pdf_path = application_pdf_path(application_id)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("SmartLoan AI", styles["Title"]))
    story.append(Paragraph("Generated Loan Application PDF", styles["Heading2"]))
    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "This PDF was generated from the current Step 1, Step 2, and Step 3 information.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 14))

    rows = [
        ["Field", "Value"],
        ["Application ID", data["application_id"]],
        ["Status", data["status"]],
        ["Applicant Name", data["applicant_name"]],
        ["First Name", data["first_name"]],
        ["Last Name", data["last_name"]],
        ["Father Name", data["father_name"]],
        ["Mother Name", data["mother_name"]],
        ["Age", data["age"]],
        ["Phone", data["phone"]],
        ["Email", data["email"]],
        ["Address", data["address"]],
        ["Occupation", data["occupation"]],
        ["Monthly Income", data["monthly_income"]],
        ["Scanned Photo", data["photo_document"]],
        ["Income Document", data["income_document"]],
        ["Identity Document", data["identity_document"]],
        ["Generated At", data["generated_at"]],
    ]

    table = Table([[safe(a), safe(b)] for a, b in rows], colWidths=[155, 325])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 16))
    story.append(Paragraph("Document Linkage", styles["Heading3"]))
    story.append(
        Paragraph(
            safe(
                f"Application #{application_id} includes applicant photo, income document, identity document, and generated PDF workflow data."
            ),
            styles["BodyText"],
        )
    )

    doc.build(story)
    return pdf_path


def get_pdf_for_extraction(application_id: int) -> Path:
    uploaded_path = uploaded_pdf_path(application_id)
    generated_path = application_pdf_path(application_id)

    if uploaded_path.exists():
        return uploaded_path

    if generated_path.exists():
        return generated_path

    raise HTTPException(status_code=404, detail="No PDF found. Create PDF first or upload PDF first.")


def extract_text_from_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = []

    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append(f"--- Page {index} ---\n{page_text}")

    text = "\n\n".join(pages).strip()
    return text or "PDF found, but no readable text extracted."


def regex_field(text: str, label: str) -> Optional[str]:
    pattern = rf"{re.escape(label)}\s*[:\-]?\s*(.+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)

    if not match:
        return None

    value = match.group(1).strip()
    value = re.split(r"\n| {2,}", value)[0].strip()
    return value or None


def extract_structured_fields(application_id: int, text: str) -> Dict[str, Any]:
    income = regex_field(text, "Monthly Income") or 0
    age = regex_field(text, "Age") or ""

    try:
        income = float(str(income).replace(",", "").strip() or 0)
    except Exception:
        income = 0

    try:
        age = int(float(str(age).strip()))
    except Exception:
        age = ""

    return {
        "application_id": application_id,
        "status": regex_field(text, "Status") or "draft",
        "applicant_name": regex_field(text, "Applicant Name") or "Not found",
        "father_name": regex_field(text, "Father Name") or "Not found",
        "mother_name": regex_field(text, "Mother Name") or "Not found",
        "age": age,
        "phone": regex_field(text, "Phone") or "Not found",
        "email": regex_field(text, "Email") or "Not found",
        "address": regex_field(text, "Address") or "Not found",
        "occupation": regex_field(text, "Occupation") or "Not found",
        "monthly_income": income,
        "documents": "photo, income document, identity document, generated application pdf",
    }


@router.post("/applications/{application_id}/generate-pdf")
@router.post("/api/applications/{application_id}/generate-pdf")
async def generate_pdf(application_id: int, payload: Optional[Dict[str, Any]] = Body(default=None)):
    pdf_path = create_application_pdf(application_id, payload)

    return {
        "message": "Generated PDF is ready.",
        "application_id": application_id,
        "filename": pdf_path.name,
        "download_url": f"/applications/{application_id}/download-pdf?t={int(datetime.now().timestamp())}",
        "received_payload": normalize_application(application_id, payload),
    }


@router.get("/applications/{application_id}/download-pdf")
@router.get("/api/applications/{application_id}/download-pdf")
async def download_pdf(application_id: int):
    pdf_path = application_pdf_path(application_id)

    if not pdf_path.exists():
        pdf_path = create_application_pdf(application_id)

    return FileResponse(
        path=str(pdf_path),
        filename=pdf_path.name,
        media_type="application/pdf",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@router.post("/applications/{application_id}/upload-loan-pdf")
@router.post("/api/applications/{application_id}/upload-loan-pdf")
async def upload_loan_pdf(application_id: int, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    target_dir = UPLOAD_DIR / str(application_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = uploaded_pdf_path(application_id)

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message": "Loan application PDF uploaded successfully.",
        "application_id": application_id,
        "filename": file.filename,
    }


@router.post("/applications/{application_id}/extract-text")
@router.post("/api/applications/{application_id}/extract-text")
async def extract_text(application_id: int):
    pdf_path = get_pdf_for_extraction(application_id)
    text = extract_text_from_pdf(pdf_path)

    return {
        "application_id": application_id,
        "source_pdf": pdf_path.name,
        "extracted_text": text,
    }


@router.post("/applications/{application_id}/extract-fields")
@router.post("/api/applications/{application_id}/extract-fields")
async def extract_fields(application_id: int):
    pdf_path = get_pdf_for_extraction(application_id)
    text = extract_text_from_pdf(pdf_path)
    fields = extract_structured_fields(application_id, text)

    return {
        "application_id": application_id,
        "fields": fields,
    }


@router.post("/applications/{application_id}/send-review")
@router.post("/api/applications/{application_id}/send-review")
async def send_review(application_id: int):
    return {
        "application_id": application_id,
        "status": "under_review",
        "message": "Application sent for review successfully.",
    }


@router.post("/applications/{application_id}/predict")
@router.post("/api/applications/{application_id}/predict")
async def predict(application_id: int):
    pdf_path = get_pdf_for_extraction(application_id)
    text = extract_text_from_pdf(pdf_path)
    fields = extract_structured_fields(application_id, text)

    income = float(fields.get("monthly_income") or 0)
    age = int(fields.get("age") or 0)
    occupation = str(fields.get("occupation") or "")

    if income >= 50000 and 21 <= age <= 60 and occupation:
        decision = "Low Risk / Recommended"
        confidence = "90%"
    elif income >= 30000:
        decision = "Medium Risk / Needs Review"
        confidence = "72%"
    else:
        decision = "High Risk / Manual Review Required"
        confidence = "60%"

    return {
        "application_id": application_id,
        "recommended_approval": decision,
        "monthly_income": income,
        "age": age,
        "occupation": occupation,
        "confidence": confidence,
        "summary": "Prediction generated from extracted PDF fields.",
    }
