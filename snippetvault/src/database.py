import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from shared.config import get_db_path


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    '''
    Establishes and configures a connection to the SQLite database.
    If no db_path is provided, it defaults to the XDG path (~/.local/share/devdesk/snippet.db).

    '''
    # Resolves Path if not explicitly passed
    target_path = db_path or get_db_path("snippets")
    # Connect to SQLite file
    conn= sqlite3.connect(target_path)
    # Configure row_factory so results act like dictionaries instead of plain tuples.
    conn.row_factory = sqlite3.Row
    #Enable WAL mode (Write_Ahead Logging) for better multi-process concurrency
    conn.execute("PRAGMA journal_mode = WAL;")

    return conn

def init_db(db_path: Optional[Path] = None) -> None:
    '''
    Initializes the database schema and indexes defined in SYSTEM_SPEC.md
    Safe to run repeatedly (Uses IF NOT EXISTS).

    '''
    with get_connection(db_path) as conn:
        #Create main snippet table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS snippets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        code TEXT NOT NULL,
        language TEXT NOT NULL DEFAULT 'text',
        tags TEXT NOT NULL DEFAULT '',
        session_id TEXT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        #Create indexes for fast filtering
        conn.execute(" CREATE INDEX IF NOT EXISTS idx_snippets_session ON snippets(session_id);")
        conn.execute(" CREATE INDEX IF NOT EXISTS idx_snippets_language ON snippets(language);")

def create_snippet(
    title: str,
    code: str,
    language: str = "text",
    tags: str ="",
    session_id: Optional[str] = None,
    db_path: Optional[Path] = None
) -> int:
    """
    Inserts a new snippet and return its autoincremented ID.

    """

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO snippets (title, code, language, tags, session_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, code, language.lower(), tags.strip(), session_id)
        )
        return cursor.lastrowid

def get_snippet(snippet_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Retrives a single snipped by its Primary ID.
    Returns a dictionary or None if not found.

    """

    with get_connection(db_path) as conn:
        cursor = conn.execute(" SELECT * FROM snippets WHERE id = ?", (snippet_id,))
        row= cursor.fetchone()
        return dict(row) if row else None


def list_snippets(
    tag: Optional[str] = None,
    language: Optional[str] = None,
    session_id: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Searches and filters snippets with dynamic WHERE clauses.
    All filters are parameterized to prevent SQL injection.

    """

    conditions = []
    params = []

    #filter by language

    if language:
        conditions.append("language=?")
        params.append(language.lower())

    #filter by exact tag or comma-seperated tag presence
    if tag:
        conditions.append("tags LIKE ?")
        params.append(f"%{tag}%")

    #filter by WorkPulse session ID
    if session_id:
        conditions.append("session_id = ?")
        params.append(session_id)
    
    #Substring search across title, code, tags
    if query:
        conditions.append("(title LIKE ? OR code LIKE ? OR tags LIKE ?)")
        wildcard_query = f"%{query}%"
        params.extend([wildcard_query, wildcard_query, wildcard_query])
    
    #Assembly query string
    sql = "SELECT * FROM snippets"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_connection(db_path) as conn:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def delete_snippet(snippet_id: int, db_path: Optional[Path] = None) -> bool:
    """
    Deletes s snipped by ID. Returns True if a record was deleted, Fals otherwise.

    """

    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM snippets WHERE id = ?",(snippet_id,)) 

        return cursor.rowcount > 0