from datetime import datetime

from pydantic import BaseModel, Field


class MLModelCreate(BaseModel):
    model_name: str = Field(min_length=2, max_length=150)
    version: str = "v1"
    description: str | None = None


class MLModelResponse(BaseModel):
    id: int
    model_name: str
    model_type: str
    version: str

    dataset_path: str | None = None
    model_path: str | None = None

    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None

    status: str
    is_active: bool
    description: str | None = None

    created_at: datetime
    deployed_at: datetime | None = None

    model_config = {
        "from_attributes": True
    }
