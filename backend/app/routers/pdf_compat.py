from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models.application import Application
from app.routers.fixed_pdf import (
    update_application_from_payload,
    create_full_fixed_pdf,
    save_generated_document,
)


router = APIRouter(prefix="/applications", tags=["PDF Compatibility"])


def get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return application


def check_permission(current_user, application: Application) -> None:
    if getattr(current_user, "role", None) != "admin" and application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")


@router.post("/{application_id}/generate-dynamic-pdf")
def compat_generate_dynamic_pdf(
    application_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_permission(current_user, application)

    if payload:
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


@router.get("/{application_id}/download-pdf")
def compat_download_pdf(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_permission(current_user, application)

    pdf_path = create_full_fixed_pdf(db, application)
    save_generated_document(db, application, pdf_path)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )


@router.post("/{application_id}/generate-pdf")
def compat_generate_pdf_json(
    application_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    check_permission(current_user, application)

    if payload:
        update_application_from_payload(application, payload)
        db.add(application)
        db.commit()
        db.refresh(application)

    pdf_path = create_full_fixed_pdf(db, application)
    document = save_generated_document(db, application, pdf_path)

    return document
