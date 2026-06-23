from __future__ import annotations

import csv
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/ai-pilot", tags=["AI Pilot"])

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "90"))

RAG_CACHE_TTL_SECONDS = 45
MAX_DB_ROWS_PER_TABLE = 5000
MAX_CSV_ROWS_PER_FILE = 8000
MAX_TOTAL_RAG_DOCS = 35000

_RAG_CACHE: dict[str, Any] = {
    "time": 0,
    "docs": [],
    "summary": {},
}


class ChatRequest(BaseModel):
    question: str
    model: str | None = None


def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except Exception:
        return str(value)


def compact(value: Any, limit: int = 1800) -> str:
    text_value = str(value or "").strip()
    if len(text_value) <= limit:
        return text_value
    return text_value[:limit] + "..."


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def only_digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def clean_words(text_value: str) -> list[str]:
    stop_words = {
        "the", "and", "or", "of", "to", "a", "an", "is", "are", "me", "my",
        "give", "show", "about", "with", "this", "that", "current", "please",
        "what", "which", "how", "why", "for", "in", "on", "from", "system",
        "tell", "summary", "short", "long", "all", "find", "info", "information",
        "loan", "application", "applicant",
    }

    found = re.findall(r"[a-zA-Z0-9_]+", text_value.lower())
    return [item for item in found if len(item) > 1 and item not in stop_words]


def query_terms(question: str) -> dict[str, Any]:
    q = normalize_text(question)
    digits = only_digits(q)

    terms = set(clean_words(q))

    synonym_groups = {
        "phone": ["phone", "mobile", "number", "contact", "cell", "call"],
        "name": ["name", "applicant", "customer", "person", "user"],
        "approved": ["approve", "approved", "accept", "accepted", "grant"],
        "refused": ["refuse", "refused", "reject", "rejected", "deny", "denied"],
        "prediction": ["prediction", "predict", "risk", "confidence", "model", "ml"],
        "dataset": ["dataset", "csv", "data", "column", "row", "features"],
        "document": ["document", "pdf", "nid", "passport", "salary", "tin", "photo"],
        "review": ["review", "decision", "admin", "message", "note"],
    }

    for root, group in synonym_groups.items():
        if any(word in q for word in group):
            terms.add(root)
            terms.update(group)

    return {
        "raw": q,
        "digits": digits,
        "terms": sorted(terms),
    }


def ollama_get(path: str, timeout: int = 6) -> dict:
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
        "keep_alive": "20m",
        "options": {
            "temperature": 0.18,
            "top_p": 0.85,
            "num_predict": 700,
            "num_ctx": 8192,
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


def safe_row(row: Any) -> dict:
    try:
        data = dict(row._mapping)
    except Exception:
        try:
            data = dict(row)
        except Exception:
            data = {}

    return data


def table_names(db: Session) -> list[str]:
    try:
        return inspect(db.bind).get_table_names()
    except Exception:
        return []


def table_rows(db: Session, table_name: str, limit: int = MAX_DB_ROWS_PER_TABLE) -> list[dict]:
    try:
        result = db.execute(text(f'SELECT * FROM "{table_name}" LIMIT :limit'), {"limit": limit}).fetchall()
        return [safe_row(row) for row in result]
    except Exception:
        return []


def get_reports_context(db: Session) -> dict:
    try:
        from app.routers.reports import reports_dashboard

        return reports_dashboard(db)
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "summary": {},
            "active_model": {},
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


def add_doc(docs: list[dict], title: str, source: str, data: Any, extra: dict | None = None) -> None:
    text_value = safe_json(data)

    doc = {
        "title": title,
        "source": source,
        "text": compact(text_value, 3000),
        "search_text": normalize_text(title + " " + source + " " + text_value),
        "digits": only_digits(text_value),
        "data": data,
    }

    if extra:
        doc.update(extra)

    docs.append(doc)


def scan_database_docs(db: Session, docs: list[dict]) -> None:
    ignored = {"alembic_version"}

    for table_name in table_names(db):
        if table_name in ignored:
            continue

        lower_table = table_name.lower()
        if lower_table.startswith("sqlite_"):
            continue

        rows = table_rows(db, table_name)

        for index, row in enumerate(rows):
            if len(docs) >= MAX_TOTAL_RAG_DOCS:
                return

            possible_name = (
                row.get("applicant_name")
                or row.get("customer_name")
                or row.get("name")
                or row.get("full_name")
                or row.get("model_name")
                or row.get("filename")
                or row.get("original_name")
                or ""
            )

            possible_id = (
                row.get("id")
                or row.get("application_id")
                or row.get("submission_id")
                or row.get("prediction_id")
                or index + 1
            )

            title = f"{table_name} record {possible_id}"
            if possible_name:
                title = f"{title} - {possible_name}"

            add_doc(
                docs,
                title=title,
                source=f"database.{table_name}",
                data=row,
                extra={
                    "table": table_name,
                    "record_id": possible_id,
                },
            )


def csv_numeric_and_category_summary(rows: list[dict], headers: list[str]) -> dict:
    numeric_summary = {}
    category_summary = {}

    for header in headers[:25]:
        numeric_values = []
        text_counts = {}

        for row in rows:
            value = row.get(header, "")

            try:
                numeric_values.append(float(str(value).replace(",", "")))
            except Exception:
                clean = str(value or "").strip()
                if clean:
                    text_counts[clean] = text_counts.get(clean, 0) + 1

        if numeric_values:
            numeric_summary[header] = {
                "count": len(numeric_values),
                "min": round(min(numeric_values), 4),
                "max": round(max(numeric_values), 4),
                "avg": round(sum(numeric_values) / len(numeric_values), 4),
            }
        elif text_counts:
            category_summary[header] = dict(sorted(text_counts.items(), key=lambda item: item[1], reverse=True)[:8])

    return {
        "numeric_summary": numeric_summary,
        "category_summary": category_summary,
    }


def scan_csv_file(path: Path, docs: list[dict], source_label: str) -> None:
    headers = []
    sample_rows = []
    scanned_rows = []
    total = 0

    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as file:
            reader = csv.DictReader(file)
            headers = list(reader.fieldnames or [])

            for row in reader:
                total += 1

                clean_row = {key: row.get(key, "") for key in headers[:40]}

                if len(sample_rows) < 12:
                    sample_rows.append(clean_row)

                if len(scanned_rows) < 250:
                    scanned_rows.append(clean_row)

                if len(docs) < MAX_TOTAL_RAG_DOCS:
                    row_title = f"{path.name} row {total}"
                    name = clean_row.get("applicant_name") or clean_row.get("name") or clean_row.get("customer_name") or ""
                    phone = clean_row.get("phone") or clean_row.get("mobile") or clean_row.get("contact") or ""

                    if name or phone:
                        row_title = f"{row_title} - {name} {phone}".strip()

                    add_doc(
                        docs,
                        title=row_title,
                        source=f"dataset.{path.name}",
                        data=clean_row,
                        extra={
                            "dataset_file": path.name,
                            "row_number": total,
                        },
                    )

                if total >= MAX_CSV_ROWS_PER_FILE:
                    break

    except Exception as exc:
        add_doc(
            docs,
            title=f"Dataset read error: {path.name}",
            source=f"dataset.{path.name}",
            data={"file_name": path.name, "error": str(exc)},
        )
        return

    summary = csv_numeric_and_category_summary(scanned_rows, headers)

    add_doc(
        docs,
        title=f"Dataset summary: {path.name}",
        source=source_label,
        data={
            "file_name": path.name,
            "headers": headers,
            "rows_scanned": total,
            "sample_rows": sample_rows,
            "numeric_summary": summary["numeric_summary"],
            "category_summary": summary["category_summary"],
        },
    )


def scan_uploaded_dataset_docs(report: dict, docs: list[dict]) -> None:
    seen = set()

    for model in report.get("models", []) or []:
        raw = model.get("raw") or {}

        for key in ["dataset_path", "dataset_file", "dataset"]:
            path = resolve_path(raw.get(key) or model.get(key))

            if path and str(path) not in seen:
                seen.add(str(path))
                scan_csv_file(path, docs, f"ml_model_dataset.{model.get('model_name') or 'model'}")

    roots = [
        Path.cwd() / "uploads",
        Path.cwd() / "uploads" / "mlops",
        Path(__file__).resolve().parents[2] / "uploads",
    ]

    for root in roots:
        if not root.exists():
            continue

        for path in list(root.rglob("*.csv"))[:40]:
            if str(path) not in seen:
                seen.add(str(path))
                scan_csv_file(path, docs, "uploaded_csv_dataset")


def build_rag_index(db: Session, force_refresh: bool = False) -> dict:
    now = time.time()

    if not force_refresh and _RAG_CACHE["docs"] and now - float(_RAG_CACHE["time"]) < RAG_CACHE_TTL_SECONDS:
        return {
            "docs": _RAG_CACHE["docs"],
            "summary": _RAG_CACHE.get("summary", {}),
        }

    report = get_reports_context(db)
    docs: list[dict] = []

    add_doc(docs, "SmartLoan report summary", "reports.summary", report.get("summary", {}))
    add_doc(docs, "Active deployed model", "ml.active_model", report.get("active_model", {}))
    add_doc(docs, "Document processing summary", "documents.summary", report.get("documents", {}))
    add_doc(docs, "Review message summary", "review.messages", report.get("review_messages", {}))

    for section_name in ["applications", "models", "predictions", "reviews", "comparison", "model_monitoring"]:
        for item in (report.get(section_name) or [])[:80]:
            add_doc(docs, f"{section_name} item", f"reports.{section_name}", item)

    scan_database_docs(db, docs)
    scan_uploaded_dataset_docs(report, docs)

    _RAG_CACHE["time"] = now
    _RAG_CACHE["docs"] = docs[:MAX_TOTAL_RAG_DOCS]
    _RAG_CACHE["summary"] = report.get("summary", {})

    return {
        "docs": _RAG_CACHE["docs"],
        "summary": _RAG_CACHE["summary"],
    }


def score_doc(doc: dict, parsed: dict) -> int:
    q = parsed["raw"]
    terms = parsed["terms"]
    digits = parsed["digits"]

    text_value = doc.get("search_text", "")
    doc_digits = doc.get("digits", "")

    score = 0

    if digits and digits in doc_digits:
        score += 500

    if digits and doc_digits.endswith(digits[-8:]):
        score += 250

    for term in terms:
        if not term:
            continue

        if term in text_value:
            score += 25

        if term in normalize_text(doc.get("title")):
            score += 45

        if term in normalize_text(doc.get("source")):
            score += 15

    if "dataset" in q or "csv" in q or "data" in q:
        if "dataset" in normalize_text(doc.get("source")):
            score += 60

    if "phone" in q or "number" in q or "mobile" in q or digits:
        if any(key in text_value for key in ["phone", "mobile", "contact"]):
            score += 40

    if "name" in q or "applicant" in q or "tell me about" in q:
        if any(key in text_value for key in ["applicant_name", "customer_name", "name", "full_name"]):
            score += 40

    if "review" in q or "approve" in q or "refuse" in q or "decision" in q:
        if "review" in normalize_text(doc.get("source")) or "decision" in text_value:
            score += 40

    if "model" in q or "prediction" in q or "risk" in q:
        if "ml" in normalize_text(doc.get("source")) or "prediction" in text_value:
            score += 40

    return score


def retrieve(question: str, docs: list[dict], top_k: int = 12) -> list[dict]:
    parsed = query_terms(question)
    scored = []

    for doc in docs:
        score = score_doc(doc, parsed)

        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)

    if scored:
        return [doc for _, doc in scored[:top_k]]

    return docs[:top_k]


def direct_rag_answer(question: str, retrieved_docs: list[dict], summary: dict) -> str:
    parsed = query_terms(question)
    digits = parsed["digits"]

    lines = []

    exact_docs = []
    if digits:
        exact_docs = [doc for doc in retrieved_docs if digits in doc.get("digits", "") or doc.get("digits", "").endswith(digits[-8:])]

    person_like_terms = [term for term in parsed["terms"] if term not in ["phone", "mobile", "number", "review", "model", "prediction", "dataset", "document"]]
    if not exact_docs and person_like_terms:
        for doc in retrieved_docs:
            text_value = doc.get("search_text", "")
            if any(term in text_value for term in person_like_terms):
                exact_docs.append(doc)

    if exact_docs:
        lines.append("I found matching SmartLoan records:")
        lines.append("")

        for doc in exact_docs[:6]:
            data = doc.get("data", {})
            lines.append(f"- Source: {doc.get('title')}")

            if isinstance(data, dict):
                important_keys = [
                    "application_id", "submission_id", "prediction_id",
                    "applicant_name", "name", "full_name", "customer_name",
                    "phone", "mobile", "contact", "email", "address",
                    "occupation", "monthly_income", "status", "decision",
                    "result", "risk_level", "confidence",
                ]

                shown = False
                for key in important_keys:
                    if key in data and data.get(key) not in [None, ""]:
                        lines.append(f"  {key}: {data.get(key)}")
                        shown = True

                if not shown:
                    lines.append(f"  data: {compact(safe_json(data), 600)}")

            else:
                lines.append(f"  data: {compact(data, 600)}")

            lines.append("")

        return "\n".join(lines).strip()

    lines.extend([
        "I searched SmartLoan project records and uploaded datasets, but I did not find an exact matching person/phone/application record for your question.",
        "",
        "Current project summary:",
        f"- Applications: {summary.get('applications', 0)}",
        f"- Predictions: {summary.get('predictions', 0)}",
        f"- Approved: {summary.get('approved', 0)}",
        f"- Refused: {summary.get('refused', 0)}",
        f"- Pending review: {summary.get('pending_review', 0)}",
        "",
        "Most relevant sources checked:",
    ])

    for doc in retrieved_docs[:6]:
        lines.append(f"- {doc.get('title')} ({doc.get('source')})")

    return "\n".join(lines)


def build_prompt(question: str, retrieved_docs: list[dict], summary: dict) -> str:
    clean_docs = []

    for doc in retrieved_docs[:12]:
        clean_docs.append({
            "title": doc.get("title"),
            "source": doc.get("source"),
            "data": doc.get("data"),
        })

    return f"""
You are SmartLoan AI Pilot.

Important behavior:
1. First understand/paraphrase the user's question.
2. Search meaning from the RAG context, not just exact words.
3. If the user asks about a name, phone, applicant, application, model, prediction, review, document, or dataset, use the matching context.
4. If exact data exists, answer with exact fields.
5. If data is missing, say clearly that no exact matching record was found.
6. Do not mention backend, API, JSON, timeout, or implementation.
7. Keep the answer clear and useful.

Project summary:
{safe_json(summary)}

Retrieved SmartLoan RAG context:
{safe_json(clean_docs)}

User question:
{question}

Final answer:
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
        "message": "AI Pilot is ready with smart RAG and Ollama.",
    }


@router.get("/context")
def ai_pilot_context(db: Session = Depends(get_db), refresh: bool = False):
    rag = build_rag_index(db, force_refresh=refresh)

    return {
        "ok": True,
        "context": {
            "summary": rag["summary"],
        },
        "rag": {
            "documents_indexed": len(rag["docs"]),
        },
    }


@router.get("/debug-rag")
def debug_rag(question: str, db: Session = Depends(get_db), refresh: bool = False):
    rag = build_rag_index(db, force_refresh=refresh)
    retrieved_docs = retrieve(question, rag["docs"], top_k=12)

    return {
        "ok": True,
        "question": question,
        "documents_indexed": len(rag["docs"]),
        "retrieved": [
            {
                "title": doc.get("title"),
                "source": doc.get("source"),
                "data": doc.get("data"),
            }
            for doc in retrieved_docs
        ],
    }


@router.get("/warmup")
def ai_pilot_warmup(model: str = DEFAULT_OLLAMA_MODEL):
    result = ollama_generate(model=model, prompt="Reply with only: SmartLoan AI ready.", timeout=120)

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

    rag = build_rag_index(db)
    docs = rag["docs"]
    summary = rag["summary"]

    retrieved_docs = retrieve(question, docs, top_k=12)
    prompt = build_prompt(question, retrieved_docs, summary)

    ollama_result = ollama_generate(model=model, prompt=prompt)

    if ollama_result.get("ok") and ollama_result.get("response"):
        return {
            "ok": True,
            "source": "ollama_smart_rag",
            "model": model,
            "answer": ollama_result["response"],
            "context_summary": summary,
            "rag": {
                "documents_indexed": len(docs),
                "retrieved": len(retrieved_docs),
            },
        }

    return {
        "ok": True,
        "source": "smart_rag_fallback",
        "model": "SmartLoan Smart RAG",
        "answer": direct_rag_answer(question, retrieved_docs, summary),
        "context_summary": summary,
        "rag": {
            "documents_indexed": len(docs),
            "retrieved": len(retrieved_docs),
        },
    }
