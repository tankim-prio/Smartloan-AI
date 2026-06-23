
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
