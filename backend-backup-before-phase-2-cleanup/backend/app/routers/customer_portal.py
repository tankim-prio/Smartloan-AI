
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from pathlib import Path
from datetime import datetime
import sqlite3
import hashlib
import secrets
import json

router = APIRouter(prefix="/api/v1/customer-portal", tags=["Customer Portal"])

DB_PATH = Path(__file__).resolve().parents[2] / "smartloan_customer_portal.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        password_salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'customer',
        status TEXT NOT NULL DEFAULT 'active',
        permissions TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customer_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_email TEXT NOT NULL,
        applicant_name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        occupation TEXT,
        monthly_income TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        review_status TEXT NOT NULL DEFAULT 'not_submitted',
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000
    ).hex()


def customer_row_to_dict(row):
    permissions = json.loads(row["permissions"] or "[]")

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "role": row["role"],
        "rawRole": row["role"],
        "status": row["status"],
        "department": "Customer Portal",
        "designation": "Customer",
        "branch": "Online Customer",
        "permissions": permissions,
        "permission_count": len(permissions),
        "accountType": "customer",
        "created_at": row["created_at"],
    }


class CustomerRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str


class CustomerLoginRequest(BaseModel):
    email: EmailStr
    password: str


class CustomerApplicationRequest(BaseModel):
    customer_email: EmailStr
    applicant_name: str
    phone: str | None = None
    address: str | None = None
    occupation: str | None = None
    monthly_income: str | None = None
    status: str = "draft"
    review_status: str = "not_submitted"
    payload: dict = {}


@router.on_event("startup")
def startup():
    init_db()


@router.get("/health")
def health():
    init_db()
    return {"status": "ok", "database": str(DB_PATH)}


@router.post("/register")
def register_customer(data: CustomerRegisterRequest):
    init_db()

    name = data.name.strip()
    email = data.email.lower().strip()
    phone = data.phone.strip()
    password = data.password

    if not name or not email or not phone or len(password) < 6:
        raise HTTPException(status_code=400, detail="Invalid customer account information.")

    permissions = ["Apply Page", "Profile"]
    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)

    conn = get_conn()
    cur = conn.cursor()

    existing = cur.execute("SELECT * FROM customers WHERE email = ?", (email,)).fetchone()

    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail="Customer already exists with this email.")

    now = datetime.utcnow().isoformat()

    cur.execute(
        """
        INSERT INTO customers
        (name, email, phone, password_hash, password_salt, role, status, permissions, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            email,
            phone,
            password_hash,
            salt,
            "customer",
            "active",
            json.dumps(permissions),
            now,
        )
    )

    conn.commit()

    row = cur.execute("SELECT * FROM customers WHERE email = ?", (email,)).fetchone()
    conn.close()

    return {
        "message": "Customer account created successfully. Please login.",
        "customer": customer_row_to_dict(row),
    }


@router.post("/login")
def login_customer(data: CustomerLoginRequest):
    init_db()

    email = data.email.lower().strip()
    password = data.password

    conn = get_conn()
    cur = conn.cursor()

    row = cur.execute("SELECT * FROM customers WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Customer account not found.")

    password_hash = hash_password(password, row["password_salt"])

    if password_hash != row["password_hash"]:
        raise HTTPException(status_code=401, detail="Incorrect password.")

    return {
        "message": "Customer login successful.",
        "user": customer_row_to_dict(row),
    }


@router.get("/customers")
def list_customers():
    init_db()

    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    conn.close()

    return {"customers": [customer_row_to_dict(row) for row in rows]}


@router.post("/applications")
def create_customer_application(data: CustomerApplicationRequest):
    init_db()

    email = data.customer_email.lower().strip()

    conn = get_conn()
    cur = conn.cursor()

    customer = cur.execute("SELECT * FROM customers WHERE email = ?", (email,)).fetchone()

    if not customer:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer not found.")

    now = datetime.utcnow().isoformat()

    cur.execute(
        """
        INSERT INTO customer_applications
        (customer_email, applicant_name, phone, address, occupation, monthly_income, status, review_status, payload, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            email,
            data.applicant_name,
            data.phone,
            data.address,
            data.occupation,
            data.monthly_income,
            data.status,
            data.review_status,
            json.dumps(data.payload),
            now,
            now,
        )
    )

    conn.commit()
    app_id = cur.lastrowid
    conn.close()

    return {
        "message": "Customer application saved.",
        "application_id": app_id,
    }


@router.get("/applications")
def list_customer_applications(email: EmailStr):
    init_db()

    customer_email = email.lower().strip()

    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT * FROM customer_applications
        WHERE customer_email = ?
        ORDER BY id DESC
        """,
        (customer_email,)
    ).fetchall()

    conn.close()

    applications = []

    for row in rows:
        applications.append({
            "id": row["id"],
            "customer_email": row["customer_email"],
            "applicant_name": row["applicant_name"],
            "phone": row["phone"],
            "address": row["address"],
            "occupation": row["occupation"],
            "monthly_income": row["monthly_income"],
            "status": row["status"],
            "review_status": row["review_status"],
            "payload": json.loads(row["payload"] or "{}"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    return {"applications": applications}
