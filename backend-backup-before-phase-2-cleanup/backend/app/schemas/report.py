from pydantic import BaseModel


class StatusCountResponse(BaseModel):
    status: str
    count: int


class DashboardOverviewResponse(BaseModel):
    total_applications: int
    draft_applications: int
    pending_reviews: int
    approved_applications: int
    rejected_applications: int
    need_more_information: int

    total_predictions: int
    low_risk_predictions: int
    medium_risk_predictions: int
    high_risk_predictions: int

    total_reviews: int
    total_users: int

    active_model_name: str | None = None
    active_model_version: str | None = None


class MonthlyApplicationReportResponse(BaseModel):
    month: str
    total_applications: int


class PredictionReportResponse(BaseModel):
    total_predictions: int
    low_risk: int
    medium_risk: int
    high_risk: int
    recommended_approval: int
    manual_review: int
    not_recommended: int


class ReviewReportResponse(BaseModel):
    total_reviews: int
    approved: int
    rejected: int
    need_more_information: int
