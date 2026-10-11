import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from shared.config import get_db_path


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Establishes connection to the WorkPulse SQLite database (~/.local/share/devdesk/workpulse.db).
    """
    target_path = db_path or get_db_path("workpulse")
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """
    Creates the sessions table defined in SYSTEM_SPEC.md.
    """
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                started_at DATETIME NOT NULL,
                ended_at DATETIME DEFAULT NULL,
                status TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}'
            );
        """)


def start_session(
    title: str,
    duration_minutes: int,
    metadata: Optional[Dict[str, Any]] = None,
    db_path: Optional[Path] = None
) -> str:
    """
    Creates a new ACTIVE session and returns its unique ID (slug with date + short UUID).
    """
    session_id = f"{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
    started_at = datetime.now().isoformat()
    meta_str = json.dumps(metadata or {})

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, title, duration_minutes, started_at, status, metadata_json)
            VALUES (?, ?, ?, ?, 'ACTIVE', ?)
            """,
            (session_id, title, duration_minutes, started_at, meta_str)
        )
    return session_id


def get_active_session(db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Finds the currently running session (status == 'ACTIVE'), if any.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE status = 'ACTIVE' ORDER BY started_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["metadata"] = json.loads(res.get("metadata_json") or "{}")
        return res


def finish_session(
    session_id: str,
    status: str = "COMPLETED",
    additional_metadata: Optional[Dict[str, Any]] = None,
    db_path: Optional[Path] = None
) -> bool:
    """
    Marks a session as COMPLETED or ABORTED and merges any new metadata.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT metadata_json FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if not row:
            return False

        existing_meta = json.loads(row["metadata_json"] or "{}")
        if additional_metadata:
            existing_meta.update(additional_metadata)

        ended_at = datetime.now().isoformat()
        conn.execute(
            """
            UPDATE sessions
            SET status = ?, ended_at = ?, metadata_json = ?
            WHERE id = ?
            """,
            (status, ended_at, json.dumps(existing_meta), session_id)
        )
        return True


def list_sessions(limit: int = 10, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Retrieves the most recent work sessions.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        )
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            item["metadata"] = json.loads(item.get("metadata_json") or "{}")
            results.append(item)
        return results