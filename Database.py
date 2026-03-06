# database.py - SQLite database for storing call logs

import sqlite3
import json
from datetime import datetime
from config import DB_FILE


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_sid TEXT UNIQUE NOT NULL,
            caller_number TEXT,
            caller_name TEXT,
            call_reason TEXT,
            urgency TEXT,           -- 'low', 'medium', 'high'
            outcome TEXT,           -- 'transferred', 'voicemail', 'spam_blocked'
            summary TEXT,           -- Written summary by Claude
            transcript TEXT,        -- Full conversation JSON
            recording_url TEXT,     -- Twilio recording URL
            recording_file TEXT,    -- Local file path
            duration_seconds INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized.")


def save_call(call_sid: str, caller_number: str):
    """Create a new call record when call starts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO calls (call_sid, caller_number)
        VALUES (?, ?)
    """, (call_sid, caller_number))
    conn.commit()
    conn.close()


def update_call(call_sid: str, **kwargs):
    """Update call record with any fields."""
    if not kwargs:
        return
    conn = get_connection()
    cursor = conn.cursor()

    # Serialize transcript if it's a list/dict
    if "transcript" in kwargs and isinstance(kwargs["transcript"], (list, dict)):
        kwargs["transcript"] = json.dumps(kwargs["transcript"])

    fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [call_sid]

    cursor.execute(f"UPDATE calls SET {fields} WHERE call_sid = ?", values)
    conn.commit()
    conn.close()


def get_all_calls():
    """Get all calls ordered by newest first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calls ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_call(call_sid: str):
    """Get a single call by SID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calls WHERE call_sid = ?", (call_sid,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None