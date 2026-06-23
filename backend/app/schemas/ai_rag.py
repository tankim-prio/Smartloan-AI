from pydantic import BaseModel, Field

class AddRagDocumentRequest(BaseModel):
    title: str = Field(..., min_length=2)
    content: str = Field(..., min_length=10)
    source_type: str = "manual"

class AskRagQuestionRequest(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int = Field(3, ge=1, le=8)

class RagSource(BaseModel):
    id: int
    title: str
    source_type: str
    score: float
    preview: str

class AskRagQuestionResponse(BaseModel):
    answer: str
    sources: list[RagSource]
    confidence: float
    mode: str
