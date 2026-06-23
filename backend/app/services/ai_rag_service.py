from datetime import datetime
from fastapi import HTTPException, UploadFile
import io
import json
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.ai_rag_db import get_rag_conn, init_ai_rag_db, DB_PATH
from app.schemas.ai_rag import AddRagDocumentRequest, AskRagQuestionRequest

def clean_text(text: str) -> str:
    text = text or ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def preview_text(text: str, limit: int = 260) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."

def split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if len(part.strip()) > 20]

def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return clean_text("\n".join(pages))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read PDF text: {exc}")

def read_upload_text(file: UploadFile, file_bytes: bytes) -> str:
    filename = (file.filename or "uploaded_file").lower()
    if filename.endswith(".pdf"):
        return extract_pdf_text(file_bytes)
    return clean_text(file_bytes.decode("utf-8", errors="ignore"))

def row_to_document(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "source_type": row["source_type"],
        "content": row["content"],
        "created_at": row["created_at"],
    }

def ai_rag_health() -> dict:
    init_ai_rag_db()
    conn = get_rag_conn()
    cur = conn.cursor()
    doc_count = cur.execute("SELECT COUNT(*) AS count FROM rag_documents").fetchone()["count"]
    question_count = cur.execute("SELECT COUNT(*) AS count FROM rag_questions").fetchone()["count"]
    conn.close()
    return {
        "status": "ok",
        "service": "ai_rag_assistant",
        "database": str(DB_PATH),
        "documents": doc_count,
        "questions": question_count,
        "mode": "local_tfidf_rag",
    }

def add_document(data: AddRagDocumentRequest) -> dict:
    init_ai_rag_db()
    title = clean_text(data.title)
    content = clean_text(data.content)
    source_type = clean_text(data.source_type) or "manual"

    if len(content) < 10:
        raise HTTPException(status_code=400, detail="Document content is too short.")

    conn = get_rag_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute(
        "INSERT INTO rag_documents (title, source_type, content, created_at) VALUES (?, ?, ?, ?)",
        (title, source_type, content, now)
    )

    conn.commit()
    doc_id = cur.lastrowid
    conn.close()

    return {
        "message": "Document added to AI/RAG knowledge base.",
        "document_id": doc_id,
        "title": title,
        "characters": len(content),
    }

async def upload_document(file: UploadFile) -> dict:
    init_ai_rag_db()
    file_bytes = await file.read()
    content = read_upload_text(file, file_bytes)

    if len(content) < 10:
        raise HTTPException(status_code=400, detail="Uploaded document has no readable text.")

    return add_document(
        AddRagDocumentRequest(
            title=file.filename or "uploaded_document",
            content=content,
            source_type="upload",
        )
    )

def list_documents() -> dict:
    init_ai_rag_db()
    conn = get_rag_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM rag_documents ORDER BY id DESC").fetchall()
    conn.close()

    documents = []
    for row in rows:
        doc = row_to_document(row)
        documents.append({
            "id": doc["id"],
            "title": doc["title"],
            "source_type": doc["source_type"],
            "characters": len(doc["content"]),
            "preview": preview_text(doc["content"]),
            "created_at": doc["created_at"],
        })

    return {"documents": documents, "count": len(documents)}

def delete_document(document_id: int) -> dict:
    init_ai_rag_db()
    conn = get_rag_conn()
    cur = conn.cursor()

    existing = cur.execute("SELECT * FROM rag_documents WHERE id = ?", (document_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found.")

    cur.execute("DELETE FROM rag_documents WHERE id = ?", (document_id,))
    conn.commit()
    conn.close()

    return {"message": "Document deleted.", "document_id": document_id}

def build_answer_from_sources(question: str, ranked_sources: list[dict]) -> str:
    if not ranked_sources:
        return "I could not find enough information in the saved documents to answer this question."

    best = ranked_sources[0]
    sentences = split_sentences(best["content"])

    if not sentences:
        return f"Based on the saved document '{best['title']}', the most relevant content is: {preview_text(best['content'], 500)}"

    question_words = {
        word.lower()
        for word in re.findall(r"[a-zA-Z0-9]+", question)
        if len(word) > 2
    }

    scored_sentences = []
    for sentence in sentences:
        sentence_words = {
            word.lower()
            for word in re.findall(r"[a-zA-Z0-9]+", sentence)
            if len(word) > 2
        }
        overlap = len(question_words.intersection(sentence_words))
        scored_sentences.append((overlap, sentence))

    scored_sentences.sort(key=lambda item: item[0], reverse=True)
    selected = [sentence for score, sentence in scored_sentences[:4]]

    if not selected:
        selected = sentences[:3]

    return f"Based on the saved SmartLoan documents, {' '.join(selected)} Source: {best['title']}."

def ask_question(data: AskRagQuestionRequest) -> dict:
    init_ai_rag_db()
    question = clean_text(data.question)

    conn = get_rag_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM rag_documents ORDER BY id DESC").fetchall()

    if not rows:
        conn.close()
        return {
            "answer": "No documents are saved in the AI/RAG knowledge base yet. Please add or upload documents first.",
            "sources": [],
            "confidence": 0,
            "mode": "local_tfidf_rag",
        }

    documents = [row_to_document(row) for row in rows]
    corpus = [doc["content"] for doc in documents]

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000, ngram_range=(1, 2))

    try:
        matrix = vectorizer.fit_transform(corpus + [question])
        doc_matrix = matrix[:-1]
        question_vector = matrix[-1]
        scores = cosine_similarity(question_vector, doc_matrix).flatten()
    except Exception as exc:
        conn.close()
        raise HTTPException(status_code=500, detail=f"RAG retrieval failed: {exc}")

    ranked_indexes = scores.argsort()[::-1][:data.top_k]
    ranked_sources = []

    for idx in ranked_indexes:
        score = float(scores[idx])
        doc = documents[int(idx)]

        if score <= 0:
            continue

        ranked_sources.append({
            "id": doc["id"],
            "title": doc["title"],
            "source_type": doc["source_type"],
            "score": round(score, 4),
            "preview": preview_text(doc["content"]),
            "content": doc["content"],
        })

    answer = build_answer_from_sources(question, ranked_sources)
    confidence = round(ranked_sources[0]["score"], 4) if ranked_sources else 0

    public_sources = [
        {
            "id": source["id"],
            "title": source["title"],
            "source_type": source["source_type"],
            "score": source["score"],
            "preview": source["preview"],
        }
        for source in ranked_sources
    ]

    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO rag_questions (question, answer, sources, created_at) VALUES (?, ?, ?, ?)",
        (question, answer, json.dumps(public_sources), now)
    )

    conn.commit()
    conn.close()

    return {
        "answer": answer,
        "sources": public_sources,
        "confidence": confidence,
        "mode": "local_tfidf_rag",
    }

def recent_questions() -> dict:
    init_ai_rag_db()
    conn = get_rag_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM rag_questions ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()

    questions = []
    for row in rows:
        questions.append({
            "id": row["id"],
            "question": row["question"],
            "answer": row["answer"],
            "sources": json.loads(row["sources"] or "[]"),
            "created_at": row["created_at"],
        })

    return {"questions": questions, "count": len(questions)}
