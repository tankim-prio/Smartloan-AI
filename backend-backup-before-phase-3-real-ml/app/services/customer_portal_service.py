from datetime import datetime
from fastapi import HTTPException
import hashlib
import json
import secrets

from app.core.customer_db import get_conn, init_customer_db, DB_PATH
from app.schemas.customer_portal import (
    CustomerRegisterRequest,
    CustomerLoginRequest,
    CustomerApplicationRequest,
)


CUSTOMER_PERMISSIONS = ["Apply Page", "Profile"]


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


def health_status():
    init_customer_db()

    return {
        "status": "ok",
        "service": "customer_portal",
        "database": str(DB_PATH),
    }


def register_customer(data: CustomerRegisterRequest):
    init_customer_db()

    name = data.name.strip()
    email = data.email.lower().strip()
    phone = data.phone.strip()
    password = data.password

    if not name or not email or not phone or len(password) < 6:
        raise HTTPException(status_code=400, detail="Invalid customer account information.")

    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)
    now = datetime.utcnow().isoformat()

    conn = get_conn()
    cur = conn.cursor()

    existing = cur.execute("SELECT * FROM customers WHERE email = ?", (email,)).fetchone()

    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail="Customer already exists with this email.")

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
            json.dumps(CUSTOMER_PERMISSIONS),
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


def login_customer(data: CustomerLoginRequest):
    init_customer_db()

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


def list_customers():
    init_customer_db()

    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    conn.close()

    return {
        "customers": [customer_row_to_dict(row) for row in rows],
        "count": len(rows),
    }


def create_customer_application(data: CustomerApplicationRequest):
    init_customer_db()

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


def list_customer_applications(email: str):
    init_customer_db()

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

    return {
        "applications": applications,
        "count": len(applications),
    }
