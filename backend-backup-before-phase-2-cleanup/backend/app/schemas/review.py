from datetime import datetime

from pydantic import BaseModel, Field


class ReviewDecisionCreate(BaseModel):
    review_status: str = Field(
        pattern="^(approved|rejected|need_more_information)$"
    )
    review_note: str | None = None


class ReviewResponse(BaseModel):
    id: int
    application_id: int
    admin_id: int
    review_status: str
    review_note: str | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
