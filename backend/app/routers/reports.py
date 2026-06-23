from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/reports", tags=["Reports"])


MESSAGE_KEYS = [
    "admin_message",
    "review_message",
    "decision_note",
    "admin_note",
    "note",
    "message",
    "reason",
    "comment",
    "review_note",
    "remarks",
    "admin_response",
    "response_message",
    "decision_message",
    "refuse_reason",
    "approval_note",
]

STATUS_KEYS = [
    "decision",
    "decision_status",
    "admin_decision",
    "review_decision",
    "final_decision",
    "approval_status",
    "review_status",
    "status",
]


def json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def safe_row(row: Any) -> dict:
    try:
        data = dict(row._mapping)
    except Exception:
        try:
            data = dict(row)
        except Exception:
            data = {}

    return {key: json_value(value) for key, value in data.items()}


def get_tables(db: Session) -> list[str]:
    try:
        return inspect(db.bind).get_table_names()
    except Exception:
        return []


def table_exists(db: Session, table_name: str) -> bool:
    return table_name in get_tables(db)


def read_rows(db: Session, table_name: str, limit: int = 10000) -> list[dict]:
    if not table_exists(db, table_name):
        return []

    try:
        result = db.execute(text(f'SELECT * FROM "{table_name}" LIMIT :limit'), {"limit": limit}).fetchall()
        return [safe_row(row) for row in result]
    except Exception:
        return []


def first_value(row: dict, keys: list[str], default: Any = None) -> Any:
    for key in keys:
        if key in row and row.get(key) not in [None, ""]:
            return row.get(key)
    return default


def to_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def low(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_status(value: Any) -> str:
    text_value = low(value)

    if not text_value:
        return "pending_review"

    if text_value in ["approved", "approve", "accepted"] or "approved" in text_value:
        return "approved"

    if (
        text_value in ["refused", "refuse", "rejected", "reject", "declined", "denied"]
        or "refused" in text_value
        or "rejected" in text_value
        or "declined" in text_value
    ):
        return "refused"

    if "pending" in text_value or "review" in text_value or "submitted" in text_value:
        return "pending_review"

    if "draft" in text_value:
        return "draft"

    return text_value


def normalize_risk(value: Any) -> str:
    text_value = low(value)

    if "low" in text_value:
        return "low"
    if "medium" in text_value:
        return "medium"
    if "high" in text_value:
        return "high"

    return "unknown"


def normalize_result(value: Any) -> str:
    text_value = low(value)

    if "approval" in text_value or "approved" in text_value:
        return "recommended_approval"

    if "manual" in text_value:
        return "manual_review"

    if "reject" in text_value or "refuse" in text_value or "not" in text_value:
        return "not_recommended"

    return text_value or "unknown"


def parse_jsonish(value: Any) -> dict:
    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        return {}

    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def row_text(row: dict) -> str:
    try:
        return json.dumps(row, default=str).lower()
    except Exception:
        return str(row).lower()


def get_date(row: dict) -> str:
    return str(
        first_value(
            row,
            [
                "decision_at",
                "reviewed_at",
                "updated_at",
                "created_at",
                "submitted_at",
                "deployed_at",
                "activated_at",
            ],
            "",
        )
        or ""
    )


def sort_score(row: dict, id_keys: list[str]) -> tuple:
    row_id = 0

    for key in id_keys:
        row_id = max(row_id, to_int(row.get(key)))

    digits = "".join(ch for ch in get_date(row) if ch.isdigit())

    try:
        date_score = int(digits[-14:]) if digits else 0
    except Exception:
        date_score = 0

    return (row_id, date_score)


def get_application_id(row: dict) -> int:
    direct = to_int(first_value(row, ["application_id", "app_id", "loan_application_id"], 0))

    if direct:
        return direct

    for key in ["snapshot", "application_snapshot", "submission", "extra", "metadata", "raw"]:
        parsed = parse_jsonish(row.get(key))
        nested = to_int(first_value(parsed, ["application_id", "app_id", "loan_application_id", "id"], 0))
        if nested:
            return nested

    return 0


def get_submission_id(row: dict) -> int:
    direct = to_int(first_value(row, ["submission_id", "review_submission_id", "id"], 0))

    if direct:
        return direct

    for key in ["submission", "snapshot", "application_snapshot", "extra", "metadata", "raw"]:
        parsed = parse_jsonish(row.get(key))
        nested = to_int(first_value(parsed, ["submission_id", "review_submission_id", "id"], 0))
        if nested:
            return nested

    return 0


def extract_message(row: dict) -> str:
    for key in MESSAGE_KEYS:
        value = str(row.get(key) or "").strip()
        if value and value.lower() not in ["none", "null", "no review message", "-"]:
            return value

    for key, value in row.items():
        key_lower = key.lower()

        if any(word in key_lower for word in ["message", "note", "reason", "comment", "remark", "response"]):
            text_value = str(value or "").strip()
            if text_value and text_value.lower() not in ["none", "null", "no review message", "-"]:
                return text_value

    for key in ["submission", "snapshot", "application_snapshot", "extra", "metadata", "raw"]:
        parsed = parse_jsonish(row.get(key))
        if parsed:
            nested = extract_message(parsed)
            if nested:
                return nested

    return ""


def extract_status(row: dict) -> str:
    status = normalize_status(first_value(row, STATUS_KEYS, ""))

    if row.get("is_approved") is True:
        return "approved"

    if row.get("is_refused") is True or row.get("is_rejected") is True:
        return "refused"

    if status != "unknown":
        return status

    for key in ["submission", "snapshot", "application_snapshot", "extra", "metadata", "raw"]:
        parsed = parse_jsonish(row.get(key))
        if parsed:
            nested = extract_status(parsed)
            if nested != "unknown":
                return nested

    return "pending_review"


def applicant_name(row: dict, app_map: dict[int, dict]) -> str:
    direct = str(
        first_value(
            row,
            ["applicant_name", "customer_name", "name", "full_name"],
            "",
        )
        or ""
    ).strip()

    if direct:
        return direct

    for key in ["snapshot", "application_snapshot", "application", "raw"]:
        parsed = parse_jsonish(row.get(key))
        nested = str(first_value(parsed, ["applicant_name", "name", "full_name", "customer_name"], "") or "").strip()
        if nested:
            return nested

    app_id = get_application_id(row)
    return app_map.get(app_id, {}).get("applicant_name") or "Applicant"


def build_applications(db: Session) -> list[dict]:
    app_table = None

    for name in ["applications", "loan_applications", "application", "loan_application"]:
        if table_exists(db, name):
            app_table = name
            break

    if not app_table:
        return []

    output = []

    for row in read_rows(db, app_table):
        app_id = to_int(first_value(row, ["application_id", "app_id", "id"], 0))
        if not app_id:
            continue

        output.append(
            {
                "application_id": app_id,
                "applicant_name": str(first_value(row, ["applicant_name", "name", "full_name", "customer_name"], "Applicant") or "Applicant"),
                "status": normalize_status(first_value(row, ["status", "review_status"], "draft")),
                "created_at": get_date(row),
                "raw": row,
            }
        )

    return output


def build_models(db: Session) -> list[dict]:
    output = []

    for row in read_rows(db, "ml_models"):
        model_id = to_int(row.get("id"))

        if not model_id:
            continue

        active_raw = row.get("is_active")
        is_active = active_raw is True or str(active_raw).lower() in ["true", "1", "yes"]

        output.append(
            {
                "id": model_id,
                "model_name": str(row.get("model_name") or row.get("name") or f"Model #{model_id}"),
                "version": str(row.get("version") or "-"),
                "model_type": str(row.get("model_type") or "-"),
                "status": "active" if is_active else str(row.get("status") or "registered"),
                "is_active": is_active,
                "dataset_original_name": row.get("dataset_original_name") or "No dataset",
                "model_original_name": row.get("model_original_name") or "No model file",
                "created_at": get_date(row),
                "raw": row,
            }
        )

    output.sort(key=lambda item: item["id"], reverse=True)
    return output


def build_predictions(db: Session, models: list[dict]) -> list[dict]:
    model_map = {to_int(model.get("id")): model for model in models}
    output = []

    for row in read_rows(db, "ml_predictions"):
        prediction_id = to_int(first_value(row, ["prediction_id", "id"], 0))
        app_id = to_int(first_value(row, ["application_id", "app_id"], 0))
        model_id = to_int(row.get("model_id"))
        model = model_map.get(model_id)

        output.append(
            {
                "prediction_id": prediction_id,
                "application_id": app_id,
                "model_id": model_id,
                "model_name": model.get("model_name") if model else str(row.get("model_name") or row.get("model") or "-"),
                "model": model,
                "result": normalize_result(first_value(row, ["result", "prediction_result"], "unknown")),
                "risk_level": normalize_risk(first_value(row, ["risk_level", "risk"], "unknown")),
                "confidence": to_float(row.get("confidence")),
                "reason": str(row.get("reason") or ""),
                "created_at": get_date(row),
                "raw": row,
            }
        )

    output.sort(key=lambda item: sort_score(item, ["prediction_id", "id"]), reverse=True)
    return output


def collect_message_bank(db: Session) -> list[dict]:
    bank = []

    for table_name in get_tables(db):
        table_lower = table_name.lower()

        should_scan = (
            "review" in table_lower
            or "submission" in table_lower
            or "decision" in table_lower
            or "notification" in table_lower
            or "message" in table_lower
            or "audit" in table_lower
            or "history" in table_lower
        )

        if not should_scan:
            continue

        for row in read_rows(db, table_name):
            message = extract_message(row)
            status = extract_status(row)
            app_id = get_application_id(row)
            sub_id = get_submission_id(row)

            if not message and status in ["unknown", "pending_review"]:
                continue

            bank.append(
                {
                    "source_table": table_name,
                    "application_id": app_id,
                    "submission_id": sub_id,
                    "status": status,
                    "message": message,
                    "created_at": get_date(row),
                    "raw": row,
                }
            )

    bank.sort(key=lambda item: sort_score(item, ["submission_id", "id"]), reverse=True)
    return bank


def best_bank_match(bank: list[dict], app_id: int, sub_id: int) -> dict:
    if sub_id:
        for item in bank:
            if to_int(item.get("submission_id")) == sub_id and item.get("message"):
                return item

    if app_id:
        for item in bank:
            if to_int(item.get("application_id")) == app_id and item.get("message"):
                return item

    if sub_id:
        for item in bank:
            if to_int(item.get("submission_id")) == sub_id:
                return item

    if app_id:
        for item in bank:
            if to_int(item.get("application_id")) == app_id:
                return item

    return {}


def build_reviews(db: Session, applications: list[dict]) -> list[dict]:
    app_map = {to_int(item.get("application_id")): item for item in applications}
    message_bank = collect_message_bank(db)

    raw_reviews = []

    for table_name in get_tables(db):
        table_lower = table_name.lower()

        if "alembic" in table_lower:
            continue

        if "review" in table_lower or "submission" in table_lower or "decision" in table_lower:
            raw_reviews.extend(read_rows(db, table_name))

    output = []
    seen = set()

    for row in raw_reviews:
        sub_id = get_submission_id(row)
        app_id = get_application_id(row)
        bank_match = best_bank_match(message_bank, app_id, sub_id)

        status = extract_status(row)
        bank_status = bank_match.get("status")

        if status in ["unknown", "pending_review"] and bank_status and bank_status != "unknown":
            status = bank_status

        message = extract_message(row) or str(bank_match.get("message") or "").strip()

        name = applicant_name(row, app_map)

        if not app_id:
            app_id = to_int(bank_match.get("application_id"))

        if not sub_id:
            sub_id = to_int(bank_match.get("submission_id"))

        key = (sub_id, app_id, status, message, get_date(row))
        if key in seen:
            continue

        seen.add(key)

        output.append(
            {
                "submission_id": sub_id,
                "application_id": app_id,
                "applicant_name": name,
                "status": status,
                "decision": status,
                "review_status": status,
                "admin_message": message,
                "review_message": message,
                "decision_note": message,
                "message": message,
                "created_at": get_date(row) or str(bank_match.get("created_at") or ""),
                "raw": row,
                "message_source": bank_match.get("source_table"),
            }
        )

    output = [item for item in output if item.get("submission_id") or item.get("application_id")]
    output.sort(key=lambda item: sort_score(item, ["submission_id", "id"]), reverse=True)
    return output


def classify_document(row: dict) -> set[str]:
    text_value = row_text(row)
    found = set()

    if any(key in text_value for key in ["loan_application", "loan application", "generated_application", "application_pdf", "loan application pdf", "generated pdf"]):
        found.add("loan_application")

    if any(key in text_value for key in ["salary", "tin", "income proof", "income_document"]):
        found.add("salary_tin")

    if any(key in text_value for key in ["nid", "passport", "identity", "identity_document"]):
        found.add("identity")

    if any(key in text_value for key in ["photo", "image", "jpeg", "jpg", "png", "screenshot", "profile picture"]):
        found.add("photo")

    return found


def build_documents(db: Session, reviews: list[dict]) -> dict:
    document_rows = []

    for table_name in get_tables(db):
        table_lower = table_name.lower()

        if any(word in table_lower for word in ["document", "file", "upload"]):
            document_rows.extend(read_rows(db, table_name))

    fallback_used = False

    if not document_rows:
        document_rows = reviews
        fallback_used = True

    counts = {
        "loan_application": 0,
        "salary_tin": 0,
        "identity": 0,
        "photo": 0,
        "total_records": len(document_rows),
        "fallback_used": fallback_used,
    }

    seen = set()

    for index, row in enumerate(document_rows):
        unique_key = (
            row.get("id"),
            row.get("document_id"),
            row.get("file_id"),
            row.get("filename"),
            row.get("file_name"),
            row.get("original_name"),
            row.get("path"),
            row.get("file_path"),
            index if fallback_used else "",
        )

        if unique_key in seen:
            continue

        seen.add(unique_key)

        for doc_type in classify_document(row):
            counts[doc_type] += 1

    return counts


def latest_by_application(items: list[dict], id_key: str) -> dict[int, dict]:
    output = {}

    for item in sorted(items, key=lambda row: sort_score(row, [id_key, "id"]), reverse=True):
        app_id = to_int(item.get("application_id"))

        if app_id and app_id not in output:
            output[app_id] = item

    return output


def build_comparison(predictions: list[dict], reviews: list[dict]) -> list[dict]:
    latest_predictions = latest_by_application(predictions, "prediction_id")
    latest_reviews = latest_by_application(reviews, "submission_id")
    app_ids = sorted(set(latest_predictions.keys()) | set(latest_reviews.keys()), reverse=True)

    output = []

    for app_id in app_ids:
        prediction = latest_predictions.get(app_id)
        review = latest_reviews.get(app_id)

        ml_result = normalize_result(prediction.get("result") if prediction else "")
        risk = normalize_risk(prediction.get("risk_level") if prediction else "")
        review_decision = normalize_status(review.get("status") if review else "pending_review")

        if not prediction:
            alignment = "no_prediction"
        elif ml_result == "recommended_approval" and review_decision == "approved":
            alignment = "matched_approval"
        elif ml_result == "recommended_approval" and review_decision == "refused":
            alignment = "ml_admin_mismatch"
        elif review_decision == "pending_review":
            alignment = "waiting_admin"
        else:
            alignment = "needs_review"

        output.append(
            {
                "application_id": app_id,
                "ml_result": ml_result,
                "risk": risk,
                "confidence": to_float(prediction.get("confidence") if prediction else 0),
                "admin_decision": review_decision,
                "alignment": alignment,
            }
        )

    return output


def build_model_monitoring(models: list[dict], predictions: list[dict]) -> list[dict]:
    output = []

    for model in models:
        model_name = str(model.get("model_name") or "-")
        related = [item for item in predictions if str(item.get("model_name") or "") == model_name]

        avg_confidence = round(sum(to_float(item.get("confidence")) for item in related) / len(related)) if related else 0
        high_risk = len([item for item in related if item.get("risk_level") == "high"])

        output.append(
            {
                "model_id": model.get("id"),
                "model_name": model_name,
                "predictions": len(related),
                "avg_confidence": avg_confidence,
                "high_risk": high_risk,
                "is_active": model.get("is_active", False),
                "status": model.get("status", "registered"),
            }
        )

    return output


def count(items: list[dict], key: str, value: str) -> int:
    return len([item for item in items if item.get(key) == value])


@router.get("/dashboard")
def reports_dashboard(db: Session = Depends(get_db)):
    applications = build_applications(db)
    models = build_models(db)
    predictions = build_predictions(db, models)
    reviews = build_reviews(db, applications)
    documents = build_documents(db, reviews)
    comparison = build_comparison(predictions, reviews)
    model_monitoring = build_model_monitoring(models, predictions)

    application_ids = set()

    for collection in [applications, predictions, reviews]:
        for item in collection:
            app_id = to_int(item.get("application_id"))
            if app_id:
                application_ids.add(app_id)

    active_model = next((item for item in models if item.get("is_active")), None)

    approved = count(reviews, "status", "approved")
    refused = count(reviews, "status", "refused")
    pending = count(reviews, "status", "pending_review")

    low_risk = count(predictions, "risk_level", "low")
    medium_risk = count(predictions, "risk_level", "medium")
    high_risk = count(predictions, "risk_level", "high")

    recommended = count(predictions, "result", "recommended_approval")
    manual_review = count(predictions, "result", "manual_review")
    not_recommended = count(predictions, "result", "not_recommended")

    confidence_values = [to_float(item.get("confidence")) for item in predictions if to_float(item.get("confidence")) > 0]
    avg_confidence = round(sum(confidence_values) / len(confidence_values)) if confidence_values else 0

    messages = [item for item in reviews if str(item.get("admin_message") or "").strip()]
    approved_with_message = len([item for item in messages if item.get("status") == "approved"])
    refused_with_message = len([item for item in messages if item.get("status") == "refused"])
    no_message = len([item for item in reviews if not str(item.get("admin_message") or "").strip()])

    matched_approval = count(comparison, "alignment", "matched_approval")
    mismatch = count(comparison, "alignment", "ml_admin_mismatch")
    waiting_admin = count(comparison, "alignment", "waiting_admin")
    no_prediction = count(comparison, "alignment", "no_prediction")

    return {
        "ok": True,
        "summary": {
            "applications": len(application_ids),
            "models": len(models),
            "predictions": len(predictions),
            "reviews": len(reviews),
            "avg_confidence": avg_confidence,
            "approved": approved,
            "refused": refused,
            "pending_review": pending,
            "high_risk": high_risk,
        },
        "active_model": active_model,
        "documents": documents,
        "review_messages": {
            "messages": len(messages),
            "approved_with_message": approved_with_message,
            "refused_with_message": refused_with_message,
            "no_message": no_message,
        },
        "charts": {
            "risk": [
                {"name": "Low Risk", "value": low_risk, "color": "#16a34a"},
                {"name": "Medium Risk", "value": medium_risk, "color": "#f59e0b"},
                {"name": "High Risk", "value": high_risk, "color": "#ef4444"},
            ],
            "review": [
                {"name": "Approved", "value": approved, "color": "#16a34a"},
                {"name": "Pending", "value": pending, "color": "#f59e0b"},
                {"name": "Refused", "value": refused, "color": "#ef4444"},
            ],
            "prediction": [
                {"name": "Recommended", "value": recommended, "color": "#16a34a"},
                {"name": "Manual Review", "value": manual_review, "color": "#f59e0b"},
                {"name": "Not Recommended", "value": not_recommended, "color": "#ef4444"},
            ],
            "alignment": [
                {"name": "Matched Approval", "value": matched_approval, "color": "#16a34a"},
                {"name": "Mismatch", "value": mismatch, "color": "#ef4444"},
                {"name": "Waiting Admin", "value": waiting_admin, "color": "#f59e0b"},
                {"name": "No Prediction", "value": no_prediction, "color": "#2563eb"},
            ],
        },
        "models": models,
        "predictions": predictions,
        "reviews": reviews,
        "applications": applications,
        "comparison": comparison,
        "model_monitoring": model_monitoring,
        "insights": [
            f"Current active model is {active_model.get('model_name') if active_model else 'No active model'}.",
            "Historical predictions may include previous active models.",
            "Reports use a dedicated backend endpoint for more accurate analytics.",
            "Strong workflow: Apply ? PDF ? ML Prediction ? Send Review ? Admin Decision ? Apply Notification ? Reports.",
        ],
    }
