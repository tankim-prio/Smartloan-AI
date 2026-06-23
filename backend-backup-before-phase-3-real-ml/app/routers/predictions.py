from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.database import get_db
from app.models.application import Application
from app.models.ml_model import MLModel
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import PredictionPreviewResponse, PredictionResponse
from app.services.prediction_service import run_baseline_prediction


router = APIRouter(prefix="/predictions", tags=["Predictions"])


def get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return application


def ensure_owner_or_admin(application: Application, current_user: User):
    if current_user.role == "admin":
        return

    if application.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this application",
        )


def get_active_model_or_400(db: Session) -> MLModel:
    model = (
        db.query(MLModel)
        .filter(
            MLModel.is_active == True,
            MLModel.status == "deployed",
        )
        .first()
    )

    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active deployed ML model found. Please deploy and activate a model first.",
        )

    return model


@router.post("/applications/{application_id}/preview", response_model=PredictionPreviewResponse)
def preview_application_prediction(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    get_active_model_or_400(db)

    if not application.occupation or application.monthly_income is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application Step 2 must be completed before prediction",
        )

    return run_baseline_prediction(application)


@router.post("/applications/{application_id}/run", response_model=PredictionResponse)
def run_application_prediction(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    active_model = get_active_model_or_400(db)

    if not application.occupation or application.monthly_income is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application Step 2 must be completed before prediction",
        )

    result = run_baseline_prediction(application)

    prediction = Prediction(
        application_id=application.id,
        model_id=active_model.id,
        prediction_result=result["prediction_result"],
        risk_level=result["risk_level"],
        confidence_score=result["confidence_score"],
        reason=result["reason"],
    )

    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return prediction


@router.get("/applications/{application_id}", response_model=list[PredictionResponse])
def get_application_predictions(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = get_application_or_404(db, application_id)
    ensure_owner_or_admin(application, current_user)

    return (
        db.query(Prediction)
        .filter(Prediction.application_id == application_id)
        .order_by(Prediction.id.desc())
        .all()
    )


@router.get("/admin/all", response_model=list[PredictionResponse])
def get_all_predictions_for_admin(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return db.query(Prediction).order_by(Prediction.id.desc()).all()
