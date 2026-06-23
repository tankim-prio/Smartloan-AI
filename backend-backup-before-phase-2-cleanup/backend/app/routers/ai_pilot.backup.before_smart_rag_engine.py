from __future__ import annotations

import csv
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/ai-pilot", tags=["AI Pilot"])

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "35"))


class ChatRequest(BaseModel):
    question: str
    model: str | None = None


def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except Exception:
        return str(value)


def cut(value: Any, limit: int = 1200) -> str:
    text_value = str(value or "").strip()
    if len(text_value) <= limit:
        return text_value
    return text_value[:limit] + "..."


def words(text_value: str) -> list[str]:
    stop_words = {
        "the", "and", "or", "of", "to", "a", "an", "is", "are", "me", "my",
        "give", "show", "about", "with", "this", "that", "current", "please",
        "what", "which", "how", "why", "for", "in", "on", "from", "system",
        "tell", "summary", "short", "long", "all",
    }

    found = re.findall(r"[a-zA-Z0-9_]+", text_value.lower())
    return [item for item in found if len(item) > 2 and item not in stop_words]


def ollama_get(path: str, timeout: int = 5) -> dict:
    try:
        request = urllib.request.Request(f"{OLLAMA_BASE_URL}{path}", method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
        }


def ollama_generate(model: str, prompt: str, timeout: int = OLLAMA_TIMEOUT_SECONDS) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.15,
            "top_p": 0.85,
            "num_predict": 520,
            "num_ctx": 4096,
        },
    }

    try:
        request = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))

        return {
            "ok": True,
            "response": str(result.get("response") or "").strip(),
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
            "applications": [],
            "comparison": [],
            "model_monitoring": [],
        }


def resolve_path(raw_path: Any) -> Path | None:
    if not raw_path:
        return None

    text_path = str(raw_path).strip().replace("\\", "/")
    if not text_path:
        return None

    raw = Path(text_path)
    candidates = []

    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(Path.cwd() / raw)
        candidates.append(Path.cwd() / "backend" / raw)
        candidates.append(Path(__file__).resolve().parents[2] / raw)

    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate
        except Exception:
            pass

    return None


def read_csv_rag(path: Path, max_scan_rows: int = 400, max_sample_rows: int = 12) -> dict:
    rows = []
    headers = []
    scanned = 0

    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as file:
            reader = csv.DictReader(file)
            headers = list(reader.fieldnames or [])

            for row in reader:
                scanned += 1
                if len(rows) < max_sample_rows:
                    rows.append({key: row.get(key, "") for key in headers[:20]})
                if scanned >= max_scan_rows:
                    break
    except Exception as exc:
        return {
            "file_name": path.name,
            "error": str(exc),
            "headers": [],
            "sample_rows": [],
            "numeric_summary": {},
            "category_summary": {},
            "rows_scanned": 0,
        }

    numeric_summary = {}
    category_summary = {}

    for header in headers[:20]:
        numeric_values = []
        text_values = {}

        for row in rows:
            raw_value = row.get(header, "")

            try:
                numeric_values.append(float(str(raw_value).replace(",", "")))
            except Exception:
                clean = str(raw_value).strip()
                if clean:
                    text_values[clean] = text_values.get(clean, 0) + 1

        if numeric_values:
            numeric_summary[header] = {
                "count": len(numeric_values),
                "min": round(min(numeric_values), 4),
                "max": round(max(numeric_values), 4),
                "avg": round(sum(numeric_values) / len(numeric_values), 4),
            }
        elif text_values:
            category_summary[header] = dict(sorted(text_values.items(), key=lambda item: item[1], reverse=True)[:6])

    return {
        "file_name": path.name,
        "file_path": str(path),
        "headers": headers,
        "sample_rows": rows,
        "numeric_summary": numeric_summary,
        "category_summary": category_summary,
        "rows_scanned": scanned,
    }


def discover_uploaded_datasets(report: dict) -> list[dict]:
    datasets = []
    seen = set()

    for model in report.get("models", []) or []:
        raw = model.get("raw") or {}

        for key in ["dataset_path", "dataset_file", "dataset"]:
            path = resolve_path(raw.get(key) or model.get(key))

            if path and str(path) not in seen:
                seen.add(str(path))
                preview = read_csv_rag(path)
                preview["source_model"] = model.get("model_name")
                datasets.append(preview)

    search_roots = [
        Path.cwd() / "uploads" / "mlops",
        Path.cwd() / "uploads",
        Path(__file__).resolve().parents[2] / "uploads",
    ]

    for root in search_roots:
        if not root.exists():
            continue

        for path in list(root.rglob("*.csv"))[:30]:
            if str(path) not in seen:
                seen.add(str(path))
                preview = read_csv_rag(path)
                preview["source_model"] = "uploaded_dataset"
                datasets.append(preview)

    return datasets[:12]


def compact_context(report: dict) -> dict:
    return {
        "summary": report.get("summary", {}),
        "active_model": report.get("active_model", {}),
        "documents": report.get("documents", {}),
        "review_messages": report.get("review_messages", {}),
        "recent_models": (report.get("models") or [])[:8],
        "recent_predictions": (report.get("predictions") or [])[:14],
        "recent_reviews": (report.get("reviews") or [])[:14],
        "ml_vs_review_comparison": (report.get("comparison") or [])[:14],
        "model_monitoring": (report.get("model_monitoring") or [])[:12],
        "uploaded_datasets": discover_uploaded_datasets(report),
    }


def make_doc(title: str, source: str, body: Any, limit: int = 1600) -> dict:
    return {
        "title": title,
        "source": source,
        "text": cut(safe_json(body), limit),
    }


def build_rag_docs(context: dict) -> list[dict]:
    docs = [
        make_doc("SmartLoan report summary", "reports.summary", context.get("summary", {})),
        make_doc("Active deployed model", "ml.active_model", context.get("active_model", {})),
        make_doc("Document processing summary", "documents.summary", context.get("documents", {})),
        make_doc("Review message summary", "review.messages", context.get("review_messages", {})),
    ]

    for item in context.get("recent_models", []):
        docs.append(make_doc(f"Model registry: {item.get('model_name')}", "ml.model_registry", item))

    for item in context.get("recent_predictions", []):
        docs.append(make_doc(f"Prediction #{item.get('prediction_id')} application #{item.get('application_id')}", "ml.predictions", item))

    for item in context.get("recent_reviews", []):
        docs.append(make_doc(f"Review submission #{item.get('submission_id')} application #{item.get('application_id')}", "review.decisions", item))

    for item in context.get("ml_vs_review_comparison", []):
        docs.append(make_doc(f"ML vs Review comparison application #{item.get('application_id')}", "analysis.comparison", item))

    for item in context.get("model_monitoring", []):
        docs.append(make_doc(f"Model monitoring: {item.get('model_name')}", "ml.monitoring", item))

    for dataset in context.get("uploaded_datasets", []):
        dataset_doc = {
            "file_name": dataset.get("file_name"),
            "source_model": dataset.get("source_model"),
            "headers": dataset.get("headers"),
            "rows_scanned": dataset.get("rows_scanned"),
            "numeric_summary": dataset.get("numeric_summary"),
            "category_summary": dataset.get("category_summary"),
            "sample_rows": dataset.get("sample_rows"),
        }
        docs.append(make_doc(f"Uploaded dataset: {dataset.get('file_name')}", "datasets.uploaded", dataset_doc, limit=2400))

    return docs


def retrieve_docs(question: str, docs: list[dict], top_k: int = 7) -> list[dict]:
    query_words = words(question)

    if not query_words:
        return docs[:top_k]

    scored = []

    for doc in docs:
        title = str(doc.get("title", "")).lower()
        source = str(doc.get("source", "")).lower()
        text = str(doc.get("text", "")).lower()

        score = 0

        for word in query_words:
            if word in title:
                score += 12
            if word in source:
                score += 8
            score += min(text.count(word), 20)

        q = question.lower()

        if any(key in q for key in ["dataset", "data", "csv", "column", "row"]):
            if "dataset" in source:
                score += 35

        if any(key in q for key in ["review", "approve", "refuse", "admin", "decision"]):
            if "review" in source or "comparison" in source:
                score += 25

        if any(key in q for key in ["model", "prediction", "risk", "confidence"]):
            if "ml" in source:
                score += 25

        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)

    return [doc for _, doc in scored[:top_k]] or docs[:top_k]


def fallback_rag_answer(question: str, context: dict, retrieved_docs: list[dict]) -> str:
    summary = context.get("summary", {})
    active_model = context.get("active_model") or {}
    docs = context.get("documents", {})
    messages = context.get("review_messages", {})

    lines = [
        "I used SmartLoan RAG data to answer this because the local Ollama model did not respond in time.",
        "",
        f"Active model: {active_model.get('model_name') or 'No active model'}",
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
        f"Loan applications: {docs.get('loan_application', 0)}",
        f"Salary/TIN: {docs.get('salary_tin', 0)}",
        f"NID/Passport: {docs.get('identity', 0)}",
        f"Photos: {docs.get('photo', 0)}",
        "",
        "Review message summary:",
        f"Messages: {messages.get('messages', 0)}",
        f"No message: {messages.get('no_message', 0)}",
    ]

    if retrieved_docs:
        lines.append("")
        lines.append("Relevant RAG sources:")
        for doc in retrieved_docs[:5]:
            lines.append(f"- {doc.get('title')}")

    return "\n".join(lines)


def build_ollama_rag_prompt(question: str, retrieved_docs: list[dict], context: dict) -> str:
    compact_summary = {
        "summary": context.get("summary", {}),
        "active_model": context.get("active_model", {}),
        "documents": context.get("documents", {}),
        "review_messages": context.get("review_messages", {}),
    }

    return f"""
You are SmartLoan AI Pilot inside a loan-processing MLOps dashboard.

You must answer using ONLY the SmartLoan RAG context below.
Use the retrieved dataset previews, reports, predictions, review decisions, and model monitoring data.
Do not say "I do not have access" if the information is in the RAG context.
Do not mention timeout, backend, API, JSON, or internal implementation.
Be clear, short, and useful for an admin.

SmartLoan summary:
{safe_json(compact_summary)}

Retrieved RAG context:
{safe_json(retrieved_docs)}

User question:
{question}

Answer:
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
        "message": "AI Pilot is ready with Ollama + RAG.",
    }


@router.get("/context")
def ai_pilot_context(db: Session = Depends(get_db)):
    report = get_reports_context(db)
    context = compact_context(report)
    rag_docs = build_rag_docs(context)

    return {
        "ok": True,
        "context": context,
        "rag": {
            "documents_indexed": len(rag_docs),
            "uploaded_datasets": len(context.get("uploaded_datasets", [])),
        },
    }


@router.get("/warmup")
def ai_pilot_warmup(model: str = DEFAULT_OLLAMA_MODEL):
    prompt = "Say ready in one short sentence."
    result = ollama_generate(model=model, prompt=prompt, timeout=45)

    return {
        "ok": bool(result.get("ok")),
        "model": model,
        "message": result.get("response") or result.get("error") or "No response",
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
    rag_docs = build_rag_docs(context)
    retrieved_docs = retrieve_docs(question, rag_docs, top_k=7)

    prompt = build_ollama_rag_prompt(question, retrieved_docs, context)
    ollama_result = ollama_generate(model=model, prompt=prompt)

    if ollama_result.get("ok") and ollama_result.get("response"):
        return {
            "ok": True,
            "source": "ollama_rag",
            "model": model,
            "answer": ollama_result["response"],
            "context_summary": context.get("summary", {}),
            "rag_sources": [
                {"title": item.get("title"), "source": item.get("source")}
                for item in retrieved_docs[:6]
            ],
            "rag": {
                "documents_indexed": len(rag_docs),
                "retrieved": len(retrieved_docs),
                "uploaded_datasets": len(context.get("uploaded_datasets", [])),
            },
        }

    return {
        "ok": True,
        "source": "rag_fallback",
        "model": "SmartLoan RAG fallback",
        "answer": fallback_rag_answer(question, context, retrieved_docs),
        "context_summary": context.get("summary", {}),
        "rag_sources": [
            {"title": item.get("title"), "source": item.get("source")}
            for item in retrieved_docs[:6]
        ],
        "rag": {
            "documents_indexed": len(rag_docs),
            "retrieved": len(retrieved_docs),
            "uploaded_datasets": len(context.get("uploaded_datasets", [])),
        },
    }
