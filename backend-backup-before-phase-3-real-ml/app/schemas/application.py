from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ApplicationStepOneCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    father_name: str = Field(min_length=1, max_length=120)
    mother_name: str = Field(min_length=1, max_length=120)
    age: int = Field(gt=0, le=120)
    phone: str = Field(min_length=5, max_length=30)
    email: EmailStr
    address: str = Field(min_length=3)


class ApplicationStepTwoUpdate(BaseModel):
    occupation: str = Field(min_length=1, max_length=120)
    monthly_income: float = Field(ge=0)


class ApplicationResponse(BaseModel):
    id: int
    user_id: int

    first_name: str
    last_name: str
    father_name: str
    mother_name: str
    age: int
    phone: str
    email: str
    address: str

    occupation: str | None = None
    monthly_income: float | None = None

    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class ApplicationDocumentResponse(BaseModel):
    id: int
    application_id: int
    document_type: str
    original_file_name: str
    stored_file_name: str
    file_path: str
    content_type: str | None = None
    uploaded_at: datetime

    model_config = {
        "from_attributes": True
    }


class ExtractedTextResponse(BaseModel):
    id: int
    application_id: int
    document_id: int | None = None
    raw_text: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class ExtractedFieldResponse(BaseModel):
    id: int
    application_id: int
    field_name: str
    field_value: str
    confidence_score: float
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
