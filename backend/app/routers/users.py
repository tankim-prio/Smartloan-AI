from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserResponse


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return db.query(User).order_by(User.id.desc()).all()
