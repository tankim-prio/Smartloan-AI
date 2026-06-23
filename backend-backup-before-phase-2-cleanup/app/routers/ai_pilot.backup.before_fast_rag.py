from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/ai-pilot", tags=["AI Pilot"])

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


class ChatRequest(BaseModel):
    question: str
    model: str | None = None


def safe_text(value: Any) -> str:
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except Exception:
        return str(value)


def ollama_get(path: str, timeout: int = 8) -> dict:
    url = f"{OLLAMA_BASE_URL}{path}"

    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def ollama_generate(model: str, prompt: str, timeout: int = 90) -> dict:
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
        },
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

        return {
            "ok": True,
            "response": result.get("response", ""),
            "raw": result,
        }

    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)

        return {
            "ok": False,
            "error": detail,
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def get_reports_context(db: Session) -> dict:
    try:
        from app.routers.reports import reports_dashboard

        return reports_dashboard(db)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Reports context unavailable: {exc}",
            "summary": {},
            "active_model": None,
            "documents": {},
            "review_messages": {},
            "models": [],
            "predictions": [],
            "reviews": [],
            "comparison": [],
            "model_monitoring": [],
        }


def compact_context(report: dict) -> dict:
    models = report.get("models") or []
    predictions = report.get("predictions") or []
    reviews = report.get("reviews") or []
    comparison = report.get("comparison") or []
    model_monitoring = report.get("model_monitoring") or []

    return {
        "summary": report.get("summary", {}),
        "active_model": report.get("active_model", {}),
        "documents": report.get("documents", {}),
        "review_messages": report.get("review_messages", {}),
        "recent_models": models[:8],
        "recent_predictions": predictions[:10],
        "recent_reviews": reviews[:10],
        "ml_vs_review_comparison": comparison[:10],
        "model_monitoring": model_monitoring[:10],
        "insights": report.get("insights", []),
    }


def fallback_answer(question: str, context: dict, reason: str = "") -> str:
    summary = context.get("summary", {})
    active_model = context.get("active_model") or {}
    documents = context.get("documents", {})
    review_messages = context.get("review_messages", {})

    active_model_name = active_model.get("model_name") or "No active model"

    lines = [
        "Ollama is not available right now, so I used the SmartLoan project data context directly.",
        "",
        f"Active model: {active_model_name}",
        f"Applications: {summary.get('applications', 0)}",
        f"ML models: {summary.get('models', 0)}",
        f"Predictions: {summary.get('predictions', 0)}",
        f"Average confidence: {summary.get('avg_confidence', 0)}%",
        f"Approved: {summary.get('approved', 0)}",
        f"Refused: {summary.get('refused', 0)}",
        f"Pending review: {summary.get('pending_review', 0)}",
        f"High risk: {summary.get('high_risk', 0)}",
        "",
        "Document summary:",
        f"Loan applications: {documents.get('loan_application', 0)}",
        f"Salary/TIN: {documents.get('salary_tin', 0)}",
        f"NID/Passport: {documents.get('identity', 0)}",
        f"Photos: {documents.get('photo', 0)}",
        "",
        "Review message summary:",
        f"Messages: {review_messages.get('messages', 0)}",
        f"No message: {review_messages.get('no_message', 0)}",
        "",
        f"Your question was: {question}",
    ]

    if reason:
        lines.append("")
        lines.append(f"Ollama status: {reason}")

    return "\n".join(lines)


def build_prompt(question: str, context: dict) -> str:
    return f"""
You are SmartLoan AI Pilot, a local AI assistant inside a loan-processing MLOps platform.

Your job:
- Answer only from the SmartLoan project context below.
- Explain in clear, practical language.
- Help admins understand applications, ML predictions, review decisions, documents, and model monitoring.
- If data is missing, say what is missing.
- Keep answers concise but useful.

SmartLoan project context:
{safe_text(context)}

User question:
{question}

Answer as SmartLoan AI Pilot:
""".strip()


@router.get("/health")
def ai_pilot_health():
    tags = ollama_get("/api/tags")

    model_names = []

    if tags.get("models"):
        model_names = [item.get("name") for item in tags.get("models", []) if item.get("name")]

    return {
        "ok": True,
        "ollama_base_url": OLLAMA_BASE_URL,
        "ollama_ready": bool(model_names),
        "default_model": DEFAULT_OLLAMA_MODEL,
        "available_models": model_names,
        "message": "AI Pilot backend is ready. Ollama is ready if available_models is not empty.",
        "ollama_error": tags.get("error") if not model_names else "",
    }


@router.get("/context")
def ai_pilot_context(db: Session = Depends(get_db)):
    report = get_reports_context(db)
    return {
        "ok": True,
        "context": compact_context(report),
    }


@router.post("/chat")
def ai_pilot_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    question = payload.question.strip()

    if not question:
        return {
            "ok": False,
            "answer": "Please write a question first.",
        }

    model = payload.model or DEFAULT_OLLAMA_MODEL

    report = get_reports_context(db)
    context = compact_context(report)
    prompt = build_prompt(question, context)

    ollama_result = ollama_generate(model=model, prompt=prompt)

    if ollama_result.get("ok") and ollama_result.get("response"):
        return {
            "ok": True,
            "source": "ollama",
            "model": model,
            "answer": ollama_result["response"],
            "context_summary": context.get("summary", {}),
            "suggested_questions": [
                "Which applications need admin attention?",
                "What is the active ML model performance?",
                "Show review approval and refusal summary.",
                "Compare ML predictions with admin decisions.",
            ],
        }

    return {
        "ok": True,
        "source": "fallback",
        "model": model,
        "answer": fallback_answer(question, context, ollama_result.get("error", "")),
        "context_summary": context.get("summary", {}),
        "ollama_error": ollama_result.get("error", ""),
        "suggested_questions": [
            "Which applications need admin attention?",
            "What is the active ML model performance?",
            "Show review approval and refusal summary.",
            "Compare ML predictions with admin decisions.",
        ],
    }
