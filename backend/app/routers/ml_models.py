from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.database import get_db
from app.models.ml_model import MLModel
from app.models.user import User
from app.schemas.ml_model import MLModelCreate, MLModelResponse


router = APIRouter(prefix="/ml-models", tags=["ML Models"])


@router.post("/", response_model=MLModelResponse, status_code=status.HTTP_201_CREATED)
def create_baseline_ml_model(
    data: MLModelCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    model = MLModel(
        model_name=data.model_name,
        model_type="baseline_rule_model",
        version=data.version,
        status="created",
        is_active=False,
        accuracy=0.80,
        precision=0.78,
        recall=0.76,
        f1_score=0.77,
        description=data.description or "Baseline rule-based loan risk model.",
    )

    db.add(model)
    db.commit()
    db.refresh(model)

    return model


@router.get("/", response_model=list[MLModelResponse])
def list_ml_models(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return db.query(MLModel).order_by(MLModel.id.desc()).all()


@router.get("/active", response_model=MLModelResponse)
def get_active_ml_model(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    model = db.query(MLModel).filter(MLModel.is_active == True).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active ML model found",
        )

    return model


@router.get("/{model_id}", response_model=MLModelResponse)
def get_ml_model_details(
    model_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    model = db.query(MLModel).filter(MLModel.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ML model not found",
        )

    return model


@router.post("/{model_id}/deploy", response_model=MLModelResponse)
def deploy_ml_model(
    model_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    model = db.query(MLModel).filter(MLModel.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ML model not found",
        )

    model.status = "deployed"
    model.deployed_at = datetime.utcnow()

    db.commit()
    db.refresh(model)

    return model


@router.post("/{model_id}/set-active", response_model=MLModelResponse)
def set_active_ml_model(
    model_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    model = db.query(MLModel).filter(MLModel.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ML model not found",
        )

    if model.status != "deployed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only deployed models can be activated",
        )

    db.query(MLModel).update({MLModel.is_active: False})

    model.is_active = True

    db.commit()
    db.refresh(model)

    return model


@router.post("/{model_id}/deactivate", response_model=MLModelResponse)
def deactivate_ml_model(
    model_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    model = db.query(MLModel).filter(MLModel.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ML model not found",
        )

    model.is_active = False
    model.status = "inactive"

    db.commit()
    db.refresh(model)

    return model
