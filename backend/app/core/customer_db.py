from pathlib import Path
import os
import sqlite3


DB_PATH = Path(
    os.getenv(
        "SMARTLOAN_CUSTOMER_DB_PATH",
        str(Path(__file__).resolve().parents[2] / "smartloan_customer_portal.db")
    )
)

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_customer_db():
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
