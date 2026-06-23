from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    model_type: Mapped[str] = mapped_column(String(80), default="baseline_rule_model", nullable=False)
    version: Mapped[str] = mapped_column(String(40), default="v1", nullable=False)

    dataset_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(String(40), default="created", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
