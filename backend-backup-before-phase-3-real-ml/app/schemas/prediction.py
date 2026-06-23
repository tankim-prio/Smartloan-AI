from datetime import datetime

from pydantic import BaseModel


class PredictionResponse(BaseModel):
    id: int
    application_id: int
    model_id: int
    prediction_result: str
    risk_level: str
    confidence_score: float
    reason: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class PredictionPreviewResponse(BaseModel):
    prediction_result: str
    risk_level: str
    confidence_score: float
    reason: str
