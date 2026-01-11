# db.py
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime

DB_PATH = "data/jd_copilot.sqlite"

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,

        company TEXT NOT NULL,
        role_title TEXT NOT NULL,
        jd_link TEXT,
        jd_text TEXT,

        stage TEXT NOT NULL DEFAULT 'NEW',              -- NEW, ANALYZED, DECISION_PENDING, QUALIFIED_PREP, APPLIED, INTERVIEWING, CLOSED, DQ
        decision TEXT DEFAULT 'PENDING',                -- PENDING, QUALIFIED, UNQUALIFIED

        day0_at TEXT,                                   -- when JD dropped
        bucket_due TEXT,                                -- next SLA due date
        next_action TEXT,
        next_action_due TEXT,

        dq_reasons_json TEXT,                            -- JSON list of codes + notes

        analysis_json TEXT,                              -- full analysis JSON
        analysis_model TEXT
    )
    """)

    conn.commit()
    conn.close()

def now_iso() -> str:
    return datetime.utcnow().isoformat()

def list_opportunities() -> List[Dict[str, Any]]:
    conn = _conn()
    rows = conn.execute("""
        SELECT id, company, role_title, stage, decision, bucket_due, updated_at
        FROM opportunities
        ORDER BY updated_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_opportunity(company: str, role_title: str, jd_link: str = "", jd_text: str = "") -> int:
    conn = _conn()
    cur = conn.cursor()
    ts = now_iso()
    cur.execute("""
        INSERT INTO opportunities (
            created_at, updated_at, company, role_title, jd_link, jd_text,
            stage, decision, day0_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'NEW', 'PENDING', ?)
    """, (ts, ts, company.strip(), role_title.strip(), jd_link.strip(), jd_text, ts))
    conn.commit()
    oid = cur.lastrowid
    conn.close()
    return int(oid)

def get_opportunity(opp_id: int) -> Optional[Dict[str, Any]]:
    conn = _conn()
    row = conn.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_opportunity(opp_id: int, fields: Dict[str, Any]) -> None:
    if not fields:
        return
    conn = _conn()
    cur = conn.cursor()
    fields = dict(fields)
    fields["updated_at"] = now_iso()

    cols = ", ".join([f"{k} = ?" for k in fields.keys()])
    vals = list(fields.values()) + [opp_id]
    cur.execute(f"UPDATE opportunities SET {cols} WHERE id = ?", vals)
    conn.commit()
    conn.close()