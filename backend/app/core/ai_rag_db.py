from pathlib import Path
import os
import sqlite3

DB_PATH = Path(
    os.getenv(
        "SMARTLOAN_RAG_DB_PATH",
        str(Path(__file__).resolve().parents[2] / "smartloan_ai_rag.db")
    )
)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_rag_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_ai_rag_db():
    conn = get_rag_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rag_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        source_type TEXT NOT NULL DEFAULT 'manual',
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rag_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        sources TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()
