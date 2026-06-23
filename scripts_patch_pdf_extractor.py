from pathlib import Path

root = Path(r"F:\Course ML, DL, FL\Project\smartloan-ai")
backend = root / "backend"

service_code = r'''
from __future__ import annotations

import io
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


PDF_SEARCH_ROOTS = [
    Path("/app/uploads"),
    Path("/app/storage"),
    Path("/app/data"),
    Path("/app"),
]


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _match(pattern: str, text: str) -> str:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return _clean_text(m.group(1)) if m else ""


def _extract_money(value: str) -> str:
    if not value:
        return ""
    m = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)", value)
    return m.group(1).replace(",", "") if m else value


def extract_fields_from_text(text: str) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}

    fields["application_id"] = _match(r"Application ID\s*[:\-]?\s*([0-9]+)", text)
    fields["status"] = _match(r"Status\s*[:\-]?\s*([A-Za-z0-9_\- ]+)", text)

    fields["applicant_name"] = _match(r"Applicant Name\s*[:\-]?\s*([^\n\r]+)", text)
    fields["first_name"] = _match(r"First Name\s*[:\-]?\s*([^\n\r]+)", text)
    fields["last_name"] = _match(r"Last Name\s*[:\-]?\s*([^\n\r]+)", text)
    fields["father_name"] = _match(r"Father Name\s*[:\-]?\s*([^\n\r]+)", text)
    fields["mother_name"] = _match(r"Mother Name\s*[:\-]?\s*([^\n\r]+)", text)

    fields["age"] = _match(r"\bAge\s*[:\-]?\s*([0-9]{1,3})", text)
    fields["phone"] = _match(r"\bPhone\s*[:\-]?\s*([+0-9][0-9\-\s]{6,20})", text)
    fields["email"] = _match(r"\bEmail\s*[:\-]?\s*([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", text)
    fields["address"] = _match(r"\bAddress\s*[:\-]?\s*([^\n\r]+)", text)
    fields["occupation"] = _match(r"\bOccupation\s*[:\-]?\s*([^\n\r]+)", text)

    monthly_income_raw = _match(r"Monthly Income\s*[:\-]?\s*(?:BDT)?\s*([0-9,]+(?:\.[0-9]+)?)", text)
    fields["monthly_income"] = _extract_money(monthly_income_raw)

    fields["salary_certificate_no"] = _match(r"Certificate No\.?\s*[:\-]?\s*([A-Za-z0-9\-\/]+)", text)
    fields["salary_issue_date"] = _match(r"Issue Date\s*[:\-]?\s*([^\n\r]+)", text)
    fields["salary_employee_name"] = _match(r"Employee Name\s*[:\-]?\s*([^\n\r]+)", text)
    fields["salary_designation"] = _match(r"Designation\s*[:\-]?\s*([^\n\r]+)", text)

    salary_raw = _match(r"Monthly Salary\s*[:\-]?\s*(?:BDT)?\s*([0-9,]+(?:\.[0-9]+)?)", text)
    fields["salary_monthly_salary"] = _extract_money(salary_raw)

    fields["nid_number"] = _match(r"(?:ID\s*NO|ID\s*NO\.|NID|National\s*ID)\s*[:\-]?\s*([0-9]{6,25})", text)
    fields["date_of_birth"] = _match(r"Date\s*of\s*Birth\s*[:\-]?\s*([^\n\r]+)", text)
    fields["blood_group"] = _match(r"Blood\s*Group\s*[:\-]?\s*([A-Za-z+\-]+)", text)

    return {k: v for k, v in fields.items() if str(v).strip()}


def _extract_with_pypdf(pdf_bytes: bytes) -> Tuple[str, int]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        chunks = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            chunks.append(f"\n\n===== PAGE {i} TEXT =====\n{page_text}")
        return _clean_text("\n".join(chunks)), len(reader.pages)
    except Exception:
        return "", 0


def _ocr_image_with_tesseract(image: Any) -> str:
    try:
        import pytesseract

        try:
            return pytesseract.image_to_string(image, lang="eng+ben") or ""
        except Exception:
            return pytesseract.image_to_string(image, lang="eng") or ""
    except Exception:
        return ""


def _extract_with_pymupdf_and_ocr(pdf_bytes: bytes) -> Tuple[str, int, bool]:
    try:
        import fitz
        from PIL import Image
    except Exception:
        text, pages = _extract_with_pypdf(pdf_bytes)
        return text, pages, False

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    chunks = []
    ocr_used = False

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)

        try:
            page_text = page.get_text("text") or ""
        except Exception:
            page_text = ""

        ocr_text = ""
        if len(page_text.strip()) < 120:
            try:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = _ocr_image_with_tesseract(img)
                if ocr_text.strip():
                    ocr_used = True
            except Exception:
                ocr_text = ""

        combined = page_text
        if ocr_text.strip():
            combined = combined + "\n\n[OCR TEXT]\n" + ocr_text

        chunks.append(f"\n\n===== PAGE {page_index + 1} TEXT =====\n{combined}")

    return _clean_text("\n".join(chunks)), len(doc), ocr_used


def find_latest_pdf() -> Optional[Path]:
    candidates = []
    for base in PDF_SEARCH_ROOTS:
        if not base.exists():
            continue
        try:
            for p in base.rglob("*.pdf"):
                if ".venv" in str(p).lower() or "site-packages" in str(p).lower():
                    continue
                try:
                    candidates.append((p.stat().st_mtime, p))
                except Exception:
                    pass
        except Exception:
            pass

    if not candidates:
        return None

    candidates.sort(reverse=True, key=lambda x: x[0])
    return candidates[0][1]


def extract_loan_pdf_bytes(pdf_bytes: bytes, filename: str = "uploaded.pdf") -> Dict[str, Any]:
    text, page_count, ocr_used = _extract_with_pymupdf_and_ocr(pdf_bytes)

    if not text.strip():
        text, page_count = _extract_with_pypdf(pdf_bytes)
        ocr_used = False

    fields = extract_fields_from_text(text)

    readable_parts = [
        "SmartLoan AI Perfect PDF Extraction",
        f"File Name: {filename}",
        f"Total Pages: {page_count}",
        f"OCR Used: {'Yes' if ocr_used else 'No'}",
        "",
        "Extracted Fields:",
    ]

    if fields:
        for k, v in fields.items():
            readable_parts.append(f"{k}: {v}")
    else:
        readable_parts.append("No structured fields detected yet.")

    readable_parts.extend([
        "",
        "Full Readable PDF Text:",
        text or "No readable text found in this PDF.",
    ])

    readable_text = "\n".join(readable_parts)

    return {
        "success": True,
        "message": "PDF extracted successfully with text-layer extraction and OCR fallback.",
        "source": "perfect_pdf_extractor",
        "filename": filename,
        "page_count": page_count,
        "ocr_used": ocr_used,
        "readable_text": readable_text,
        "extracted_text": text,
        "text": text,
        "fields": fields,
        "extracted_fields": fields,
        "data": {
            "readable_text": readable_text,
            "extracted_text": text,
            "fields": fields,
            "extracted_fields": fields,
        },
    }
'''

router_code = r'''
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Request, UploadFile

from app.services.perfect_pdf_extractor_service import (
    extract_loan_pdf_bytes,
    find_latest_pdf,
)

router = APIRouter(prefix="/api/v1", tags=["Perfect PDF Extractor"])


async def _extract_from_request(
    request: Request,
    file: Optional[UploadFile] = None,
    pdf: Optional[UploadFile] = None,
    loan_pdf: Optional[UploadFile] = None,
    document: Optional[UploadFile] = None,
    upload_file: Optional[UploadFile] = None,
):
    selected_file = file or pdf or loan_pdf or document or upload_file

    if selected_file is not None:
        data = await selected_file.read()
        return extract_loan_pdf_bytes(data, selected_file.filename or "uploaded.pdf")

    latest_pdf = find_latest_pdf()
    if latest_pdf and latest_pdf.exists():
        return extract_loan_pdf_bytes(latest_pdf.read_bytes(), latest_pdf.name)

    return {
        "success": False,
        "message": "No PDF file was received and no saved PDF was found in uploads/storage.",
        "source": "perfect_pdf_extractor",
        "readable_text": "No PDF file was received and no saved PDF was found.",
        "extracted_text": "",
        "text": "",
        "fields": {},
        "extracted_fields": {},
        "data": {
            "readable_text": "No PDF file was received and no saved PDF was found.",
            "extracted_text": "",
            "fields": {},
            "extracted_fields": {},
        },
    }


@router.post("/perfect-pdf/extract")
@router.post("/perfect-pdf/extract-text")
@router.post("/{full_path:path}/extract")
@router.post("/{full_path:path}/extract-text")
async def perfect_pdf_extract(
    request: Request,
    full_path: str = "",
    file: Optional[UploadFile] = File(None),
    pdf: Optional[UploadFile] = File(None),
    loan_pdf: Optional[UploadFile] = File(None),
    document: Optional[UploadFile] = File(None),
    upload_file: Optional[UploadFile] = File(None),
):
    return await _extract_from_request(
        request=request,
        file=file,
        pdf=pdf,
        loan_pdf=loan_pdf,
        document=document,
        upload_file=upload_file,
    )
'''

(backend / "app" / "services" / "perfect_pdf_extractor_service.py").write_text(service_code, encoding="utf-8")
(backend / "app" / "routers" / "perfect_pdf_extractor.py").write_text(router_code, encoding="utf-8")

main_path = backend / "app" / "main.py"
main = main_path.read_text(encoding="utf-8")

import_line = "from app.routers.perfect_pdf_extractor import router as perfect_pdf_extractor_router\n"
include_line = "app.include_router(perfect_pdf_extractor_router)\n"

if "perfect_pdf_extractor_router" not in main:
    main = import_line + main

if include_line not in main:
    pos = main.find("app = FastAPI")
    if pos != -1:
        seen = False
        depth = 0
        insert_at = None
        for i in range(pos, len(main)):
            ch = main[i]
            if ch == "(":
                seen = True
                depth += 1
            elif ch == ")":
                depth -= 1
                if seen and depth <= 0:
                    nl = main.find("\n", i)
                    insert_at = nl + 1 if nl != -1 else len(main)
                    break
        if insert_at is not None:
            main = main[:insert_at] + include_line + main[insert_at:]
        else:
            main = main + "\n" + include_line
    else:
        main = main + "\n" + include_line

main_path.write_text(main, encoding="utf-8")

print("Perfect PDF extractor service/router created and main.py patched.")
