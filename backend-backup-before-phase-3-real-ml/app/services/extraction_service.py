import re
from pathlib import Path

from pypdf import PdfReader


def extract_text_from_pdf(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError("File does not exist")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Text extraction currently supports PDF files only")

    reader = PdfReader(str(path))
    pages_text: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages_text.append(page_text)

    return "\n".join(pages_text).strip()


def extract_basic_fields(raw_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}

    patterns = {
        "application_id": r"Application ID:\s*(.+)",
        "status": r"Status:\s*(.+)",
        "applicant_name": r"Applicant Name:\s*(.+)",
        "father_name": r"Father Name:\s*(.+)",
        "mother_name": r"Mother Name:\s*(.+)",
        "age": r"Age:\s*(.+)",
        "phone": r"Phone:\s*(.+)",
        "email": r"Email:\s*(.+)",
        "address": r"Address:\s*(.+)",
        "occupation": r"Occupation:\s*(.+)",
        "monthly_income": r"Monthly Income:\s*(.+)",
    }

    for field_name, pattern in patterns.items():
        match = re.search(pattern, raw_text, re.IGNORECASE)

        if match:
            fields[field_name] = match.group(1).strip()

    return fields
