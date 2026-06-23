from fastapi import APIRouter, File, UploadFile

from app.core.ai_rag_db import init_ai_rag_db
from app.schemas.ai_rag import AddRagDocumentRequest, AskRagQuestionRequest, AskRagQuestionResponse
from app.services.ai_rag_service import (
    ai_rag_health,
    add_document,
    upload_document,
    list_documents,
    delete_document,
    ask_question,
    recent_questions,
)

router = APIRouter(prefix="/api/v1/ai-rag", tags=["AI RAG Assistant"])

@router.on_event("startup")
def startup():
    init_ai_rag_db()

@router.get("/health")
def health():
    return ai_rag_health()

@router.post("/documents")
def documents_add(data: AddRagDocumentRequest):
    return add_document(data)

@router.post("/documents/upload")
async def documents_upload(file: UploadFile = File(...)):
    return await upload_document(file)

@router.get("/documents")
def documents_list():
    return list_documents()

@router.delete("/documents/{document_id}")
def documents_delete(document_id: int):
    return delete_document(document_id)

@router.post("/ask", response_model=AskRagQuestionResponse)
def ask(data: AskRagQuestionRequest):
    return ask_question(data)

@router.get("/questions")
def questions():
    return recent_questions()
