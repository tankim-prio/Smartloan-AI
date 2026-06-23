from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/account-management", tags=["Account Management"])


class AccountCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = ""
    role: str
    department: str | None = ""
    designation: str | None = ""
    branch: str | None = ""
    status: str | None = "active"
    password: str
    confirm_password: str
    permissions: list[str] = []
    notes: str | None = ""


class AccountStatusUpdate(BaseModel):
    status: str


VALID_ROLES = {
    "admin",
    "reviewer",
    "loan_officer",
    "ml_manager",
    "auditor",
}

VALID_STATUS = {"active", "inactive", "suspended"}


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def ensure_table(db: Session) -> None:
    dialect = db.bind.dialect.name if db.bind is not None else "sqlite"

    if dialect == "postgresql":
        create_sql = """
        CREATE TABLE IF NOT EXISTS smartloan_staff_accounts (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            role TEXT NOT NULL,
            department TEXT,
            designation TEXT,
            branch TEXT,
            status TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            permissions_json TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    else:
        create_sql = """
        CREATE TABLE IF NOT EXISTS smartloan_staff_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            role TEXT NOT NULL,
            department TEXT,
            designation TEXT,
            branch TEXT,
            status TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            permissions_json TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """

    db.execute(text(create_sql))
    db.commit()


def row_to_dict(row: Any) -> dict:
    try:
        data = dict(row._mapping)
    except Exception:
        data = dict(row)

    data.pop("password_hash", None)

    try:
        data["permissions"] = json.loads(data.get("permissions_json") or "[]")
    except Exception:
        data["permissions"] = []

    data.pop("permissions_json", None)
    return data


def normalize_permissions(role: str, permissions: list[str]) -> list[str]:
    if permissions:
        return sorted(set(permissions))

    defaults = {
        "admin": [
            "dashboard:view",
            "apply:manage",
            "review:decision",
            "ml:model_manage",
            "reports:view",
            "ai_pilot:use",
            "account:create",
        ],
        "reviewer": [
            "dashboard:view",
            "review:view",
            "review:decision",
            "reports:view",
        ],
        "loan_officer": [
            "dashboard:view",
            "apply:manage",
            "review:view",
        ],
        "ml_manager": [
            "dashboard:view",
            "ml:model_manage",
            "reports:view",
            "ai_pilot:use",
        ],
        "auditor": [
            "dashboard:view",
            "reports:view",
            "review:view",
        ],
    }

    return defaults.get(role, ["dashboard:view"])


@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db)):
    ensure_table(db)

    rows = db.execute(
        text("""
        SELECT *
        FROM smartloan_staff_accounts
        ORDER BY id DESC
        """)
    ).fetchall()

    return {
        "ok": True,
        "accounts": [row_to_dict(row) for row in rows],
    }


@router.post("/accounts")
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    ensure_table(db)

    name = payload.name.strip()
    email = payload.email.strip().lower()
    role = payload.role.strip().lower()
    status = (payload.status or "active").strip().lower()

    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")

    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role selected.")

    if status not in VALID_STATUS:
        raise HTTPException(status_code=400, detail="Invalid account status.")

    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Password and confirm password do not match.")

    existing = db.execute(
        text("SELECT id FROM smartloan_staff_accounts WHERE lower(email) = lower(:email)"),
        {"email": email},
    ).fetchone()

    if existing:
        raise HTTPException(status_code=409, detail="This email already exists.")

    permissions = normalize_permissions(role, payload.permissions)
    created_at = now_iso()

    db.execute(
        text("""
        INSERT INTO smartloan_staff_accounts (
            name, email, phone, role, department, designation, branch, status,
            password_hash, permissions_json, notes, created_at, updated_at
        )
        VALUES (
            :name, :email, :phone, :role, :department, :designation, :branch, :status,
            :password_hash, :permissions_json, :notes, :created_at, :updated_at
        )
        """),
        {
            "name": name,
            "email": email,
            "phone": payload.phone or "",
            "role": role,
            "department": payload.department or "",
            "designation": payload.designation or "",
            "branch": payload.branch or "",
            "status": status,
            "password_hash": hash_password(payload.password),
            "permissions_json": json.dumps(permissions),
            "notes": payload.notes or "",
            "created_at": created_at,
            "updated_at": created_at,
        },
    )
    db.commit()

    row = db.execute(
        text("SELECT * FROM smartloan_staff_accounts WHERE lower(email) = lower(:email)"),
        {"email": email},
    ).fetchone()

    return {
        "ok": True,
        "message": "Account created successfully.",
        "account": row_to_dict(row),
    }


@router.patch("/accounts/{account_id}/status")
def update_account_status(account_id: int, payload: AccountStatusUpdate, db: Session = Depends(get_db)):
    ensure_table(db)

    status = payload.status.strip().lower()

    if status not in VALID_STATUS:
        raise HTTPException(status_code=400, detail="Invalid account status.")

    existing = db.execute(
        text("SELECT id FROM smartloan_staff_accounts WHERE id = :id"),
        {"id": account_id},
    ).fetchone()

    if not existing:
        raise HTTPException(status_code=404, detail="Account not found.")

    db.execute(
        text("""
        UPDATE smartloan_staff_accounts
        SET status = :status, updated_at = :updated_at
        WHERE id = :id
        """),
        {
            "id": account_id,
            "status": status,
            "updated_at": now_iso(),
        },
    )
    db.commit()

    return {
        "ok": True,
        "message": f"Account status updated to {status}.",
    }


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    ensure_table(db)

    db.execute(
        text("DELETE FROM smartloan_staff_accounts WHERE id = :id"),
        {"id": account_id},
    )
    db.commit()

    return {
        "ok": True,
        "message": "Account deleted successfully.",
    }
