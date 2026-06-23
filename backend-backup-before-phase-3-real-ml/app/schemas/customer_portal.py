from pydantic import BaseModel, EmailStr, Field
from typing import Any


class CustomerRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)


class CustomerLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class CustomerApplicationRequest(BaseModel):
    customer_email: EmailStr
    applicant_name: str
    phone: str | None = None
    address: str | None = None
    occupation: str | None = None
    monthly_income: str | None = None
    status: str = "draft"
    review_status: str = "not_submitted"
    payload: dict[str, Any] = {}
