from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.database import get_db
from app.models.application import Application
from app.models.notification import Notification
from app.models.review import Review
from app.models.user import User
from app.schemas.application import ApplicationResponse
from app.schemas.review import ReviewDecisionCreate, ReviewResponse


router = APIRouter(prefix="/reviews", tags=["Reviews"])


def get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return application


@router.get("/pending", response_model=list[ApplicationResponse])
def get_pending_review_applications(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return (
        db.query(Application)
        .filter(Application.status == "pending_review")
        .order_by(Application.id.desc())
        .all()
    )


@router.get("/all", response_model=list[ReviewResponse])
def get_all_reviews(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return db.query(Review).order_by(Review.id.desc()).all()


@router.get("/application/{application_id}", response_model=list[ReviewResponse])
def get_reviews_for_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)

    if current_user.role != "admin" and application.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access these reviews",
        )

    return (
        db.query(Review)
        .filter(Review.application_id == application_id)
        .order_by(Review.id.desc())
        .all()
    )


@router.post("/{application_id}/decision", response_model=ReviewResponse)
def create_review_decision(
    application_id: int,
    data: ReviewDecisionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    application = get_application_or_404(db, application_id)

    if application.status not in ["pending_review", "need_more_information"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or need-more-information applications can be reviewed",
        )

    review = Review(
        application_id=application.id,
        admin_id=admin.id,
        review_status=data.review_status,
        review_note=data.review_note,
    )

    if data.review_status == "approved":
        application.status = "approved"
        title = "Application Approved"
        message = "Your application has been approved."

    elif data.review_status == "rejected":
        application.status = "rejected"
        title = "Application Rejected"
        message = "Your application has been rejected."

    else:
        application.status = "need_more_information"
        title = "More Information Required"
        message = "Admin requested more information for your application."

    if data.review_note:
        message = f"{message} Note: {data.review_note}"

    notification = Notification(
        user_id=application.user_id,
        application_id=application.id,
        title=title,
        message=message,
        is_read=False,
    )

    db.add(review)
    db.add(notification)
    db.commit()
    db.refresh(review)

    return review
