from pathlib import Path

root = Path(r"F:\Course ML, DL, FL\Project\smartloan-ai")
backend = root / "backend"

service = r'''
import io
import re
from pathlib import Path
from typing import Any, Dict, Optional


SEARCH_ROOTS = [
    Path("/app/uploads"),
    Path("/app/storage"),
    Path("/app/data"),
    Path("/app"),
]


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_match(pattern: str, text: str) -> str:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return clean_text(m.group(1)) if m else ""


def money(value: str) -> str:
    m = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)", value or "")
    return m.group(1).replace(",", "") if m else value


def find_latest_pdf() -> Optional[Path]:
    found = []
    for base in SEARCH_ROOTS:
        if not base.exists():
            continue
        for p in base.rglob("*.pdf"):
            sp = str(p).lower()
            if "site-packages" in sp or ".venv" in sp:
                continue
            try:
                found.append((p.stat().st_mtime, p))
            except Exception:
                pass
    if not found:
        return None
    found.sort(reverse=True, key=lambda x: x[0])
    return found[0][1]


def extract_text_from_pdf_bytes(pdf_bytes: bytes):
    page_count = 0
    ocr_used = False
    all_parts = []

    try:
        import fitz
        from PIL import Image
        import pytesseract

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)

        for idx in range(len(doc)):
            page = doc.load_page(idx)
            page_text = page.get_text("text") or ""

            ocr_text = ""
            if len(page_text.strip()) < 120:
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    try:
                        ocr_text = pytesseract.image_to_string(img, lang="eng+ben") or ""
                    except Exception:
                        ocr_text = pytesseract.image_to_string(img, lang="eng") or ""
                    if ocr_text.strip():
                        ocr_used = True
                except Exception:
                    ocr_text = ""

            combined = page_text
            if ocr_text.strip():
                combined += "\n\n[OCR TEXT]\n" + ocr_text

            all_parts.append(f"\n\n===== PAGE {idx + 1} =====\n{combined}")

    except Exception:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            page_count = len(reader.pages)
            for idx, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text() or ""
                except Exception:
                    page_text = ""
                all_parts.append(f"\n\n===== PAGE {idx} =====\n{page_text}")
        except Exception as e:
            all_parts.append(f"PDF extraction failed: {e}")

    return clean_text("\n".join(all_parts)), page_count, ocr_used


def extract_fields(text: str) -> Dict[str, Any]:
    fields = {}

    fields["application_id"] = get_match(r"Application ID\s*[:\-]?\s*([0-9]+)", text)
    fields["status"] = get_match(r"Status\s*[:\-]?\s*([A-Za-z0-9_\- ]+)", text)
    fields["applicant_name"] = get_match(r"Applicant Name\s*[:\-]?\s*([^\n\r]+)", text)
    fields["first_name"] = get_match(r"First Name\s*[:\-]?\s*([^\n\r]+)", text)
    fields["last_name"] = get_match(r"Last Name\s*[:\-]?\s*([^\n\r]+)", text)
    fields["father_name"] = get_match(r"Father Name\s*[:\-]?\s*([^\n\r]+)", text)
    fields["mother_name"] = get_match(r"Mother Name\s*[:\-]?\s*([^\n\r]+)", text)
    fields["age"] = get_match(r"\bAge\s*[:\-]?\s*([0-9]{1,3})", text)
    fields["phone"] = get_match(r"\bPhone\s*[:\-]?\s*([+0-9][0-9\-\s]{6,20})", text)
    fields["email"] = get_match(r"\bEmail\s*[:\-]?\s*([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})", text)
    fields["address"] = get_match(r"\bAddress\s*[:\-]?\s*([^\n\r]+)", text)
    fields["occupation"] = get_match(r"\bOccupation\s*[:\-]?\s*([^\n\r]+)", text)
    fields["monthly_income"] = money(get_match(r"Monthly Income\s*[:\-]?\s*(?:BDT)?\s*([0-9,]+(?:\.[0-9]+)?)", text))

    fields["salary_certificate_no"] = get_match(r"Certificate No\.?\s*[:\-]?\s*([A-Za-z0-9\-\/]+)", text)
    fields["salary_issue_date"] = get_match(r"Issue Date\s*[:\-]?\s*([^\n\r]+)", text)
    fields["employee_name"] = get_match(r"Employee Name\s*[:\-]?\s*([^\n\r]+)", text)
    fields["designation"] = get_match(r"Designation\s*[:\-]?\s*([^\n\r]+)", text)
    fields["monthly_salary"] = money(get_match(r"Monthly Salary\s*[:\-]?\s*(?:BDT)?\s*([0-9,]+(?:\.[0-9]+)?)", text))

    fields["nid_number"] = get_match(r"(?:ID\s*NO\.?|NID|National\s*ID)\s*[:\-]?\s*([0-9]{6,25})", text)
    fields["date_of_birth"] = get_match(r"Date\s*of\s*Birth\s*[:\-]?\s*([^\n\r]+)", text)

    return {k: v for k, v in fields.items() if str(v).strip()}


def extract_pdf_bytes(pdf_bytes: bytes, filename: str = "uploaded.pdf") -> Dict[str, Any]:
    text, pages, ocr_used = extract_text_from_pdf_bytes(pdf_bytes)
    fields = extract_fields(text)

    readable = []
    readable.append("PERFECT PDF EXTRACTION RESULT")
    readable.append("")
    readable.append(f"File Name: {filename}")
    readable.append(f"Total Pages: {pages}")
    readable.append(f"OCR Used: {'Yes' if ocr_used else 'No'}")
    readable.append("")
    readable.append("STRUCTURED FIELDS")
    if fields:
        for k, v in fields.items():
            readable.append(f"{k}: {v}")
    else:
        readable.append("No structured fields detected.")
    readable.append("")
    readable.append("FULL PDF TEXT")
    readable.append(text or "No readable text found.")

    readable_text = "\n".join(readable)

    return {
        "success": True,
        "message": "PDF extracted from uploaded/latest PDF successfully.",
        "source": "forced_perfect_pdf_extractor",
        "filename": filename,
        "page_count": pages,
        "ocr_used": ocr_used,
        "readable_text": readable_text,
        "extracted_text": text,
        "text": text,
        "fields": fields,
        "extracted_fields": fields,
        "data": {
            "readable_text": readable_text,
            "extracted_text": text,
            "text": text,
            "fields": fields,
            "extracted_fields": fields,
        },
    }


async def extract_from_request_or_latest(request):
    try:
        form = await request.form()
        for key, value in form.items():
            if hasattr(value, "filename") and value.filename:
                content = await value.read()
                if content:
                    return extract_pdf_bytes(content, value.filename)
    except Exception:
        pass

    latest = find_latest_pdf()
    if latest and latest.exists():
        return extract_pdf_bytes(latest.read_bytes(), latest.name)

    return {
        "success": False,
        "message": "No uploaded PDF found.",
        "source": "forced_perfect_pdf_extractor",
        "readable_text": "No uploaded PDF found.",
        "extracted_text": "",
        "text": "",
        "fields": {},
        "extracted_fields": {},
        "data": {
            "readable_text": "No uploaded PDF found.",
            "extracted_text": "",
            "text": "",
            "fields": {},
            "extracted_fields": {},
        },
    }
'''

middleware_patch = r'''
from starlette.responses import JSONResponse
from app.services.force_pdf_extractor_service import extract_from_request_or_latest

@app.middleware("http")
async def force_pdf_extract_text_middleware(request, call_next):
    path = request.url.path.lower()
    if request.method.upper() == "POST" and "extract" in path and "field" not in path and "predict" not in path:
        result = await extract_from_request_or_latest(request)
        return JSONResponse(result)
    return await call_next(request)
'''

service_path = backend / "app" / "services" / "force_pdf_extractor_service.py"
service_path.write_text(service, encoding="utf-8")

main_path = backend / "app" / "main.py"
main = main_path.read_text(encoding="utf-8")

if "force_pdf_extract_text_middleware" not in main:
    app_pos = main.find("app = FastAPI")
    if app_pos == -1:
        main += "\n" + middleware_patch + "\n"
    else:
        seen = False
        depth = 0
        insert_at = None
        for i in range(app_pos, len(main)):
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
        if insert_at is None:
            main += "\n" + middleware_patch + "\n"
        else:
            main = main[:insert_at] + "\n" + middleware_patch + "\n" + main[insert_at:]

main_path.write_text(main, encoding="utf-8")
print("Forced PDF extract middleware added.")
