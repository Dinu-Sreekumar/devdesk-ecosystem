# SnippetVault Technical Documentation
**Utility:** `vault` | **Service Port:** `8765` | **Storage:** `$XDG_DATA_HOME/devdesk/snippets.db`

---

## 1. Overview & Architectural Philosophy

Modern software development requires capturing shell one-liners, complex SQL queries, API payloads, and error traces. Traditional web-based pastebins introduce security risks (leaking credentials or proprietary code), network latency, and context switching.

**SnippetVault** is a local-first, offline knowledge stash and REST daemon designed to solve this friction. It operates under two primary modes:
1. **Direct CLI Mode:** Operates directly against SQLite for near-instant execution (<5ms).
2. **Daemon Mode (`vault serve`):** Exposes a high-performance FastAPI server on port `8765` so external tools (such as WorkPulse) can query, filter, and link snippets programmatically.

---

## 2. Storage & Database Architecture

SnippetVault adheres strictly to the **POSIX XDG Base Directory Specification**, storing its database file at:
```text
$XDG_DATA_HOME/devdesk/snippets.db  (defaults to ~/.local/share/devdesk/snippets.db)
```

### 2.1 SQLite Schema & Indexing
Persistence is managed with Python's standard `sqlite3` engine using parameterized queries to prevent SQL injection:

```sql
CREATE TABLE IF NOT EXISTS snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    code TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'text',
    tags TEXT NOT NULL DEFAULT '',           -- Comma-delimited: "python,sql,auth"
    session_id TEXT DEFAULT NULL,             -- Associated WorkPulse session UUID
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_snippets_session ON snippets(session_id);
CREATE INDEX IF NOT EXISTS idx_snippets_language ON snippets(language);
```

### 2.2 Concurrency & WAL Mode
On connection initialization, SnippetVault executes:
```sql
PRAGMA journal_mode = WAL;
```
Write-Ahead Logging (WAL) enables multiple read operations to proceed concurrently while a write operation is in progress, preventing `database is locked` errors when both the CLI and the background FastAPI server access the file simultaneously.

---

## 3. Unix Stdin Piping Mechanics

SnippetVault embraces the Unix philosophy: *Write programs that do one thing and do it well, and that work together through text streams.*

To support piping (`cat script.py | vault save ...`), the CLI inspects the terminal state:
```python
if not sys.stdin.isatty():
    piped_content = sys.stdin.read().strip()
```
* **If `sys.stdin.isatty()` is `False`:** Standard input is connected to a pipe or file redirect; SnippetVault reads stdin automatically.
* **If `sys.stdin.isatty()` is `True`:** SnippetVault expects code as a positional argument or prompts the user.

---

## 4. REST API Specification (Port 8765)

When run as a daemon (`vault serve`), SnippetVault exposes the following REST interface:

### `GET /health`
* **Response (200 OK):**
```json
{
  "service": "snippetvault",
  "status": "healthy",
  "version": "0.1.0"
}
```

### `POST /api/v1/snippets`
* **Request Body:**
```json
{
  "title": "Database Migration Script",
  "code": "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;",
  "language": "sql",
  "tags": "db,migration",
  "session_id": "20261011-d1aebe"
}
```
* **Response (201 Created):** Returns full `SnippetResponse` object.

### `GET /api/v1/snippets`
* **Query Parameters:**
  * `tag` (string): Filter by tag substring.
  * `language` (string): Exact match on language.
  * `session_id` (string): Filter by WorkPulse session ID.
  * `q` (string): Full-text substring search across title, code, and tags.
  * `limit` (int, default 50): Page size.
* **Response (200 OK):** Array of `SnippetResponse` objects.

### `GET /api/v1/snippets/{id}`
* **Response (200 OK):** Returns single snippet object.
* **Response (404 Not Found):** Returns standard `ErrorEnvelope`:
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Snippet with id 42 does not exist",
    "details": {}
  }
}
```

### `DELETE /api/v1/snippets/{id}`
* **Response:** `204 No Content` on successful deletion, or `404 Not Found`.

---

## 5. Developer Use Cases

1. **Terminal Command & Pipeline Stashing:**
   ```bash
   history | tail -n 20 | vault save "Docker build sequence" --lang bash --tag docker
   ```
2. **Context-Linked Coding Sessions:**
   WorkPulse automatically tags snippets created during an active sprint with the active `--session` identifier. Later, developers can retrieve all code produced during a 25-minute Pomodoro block:
   ```bash
   vault list --session 20261011-d1aebe
   ```
3. **Syntax Highlighted Viewing:**
   Inspect snippets in the terminal with line numbers and Monokai coloring:
   ```bash
   vault get 8
   ```

---

## 6. Related Documentation
* [Master CLI Reference](cli-reference.md)
* [NetWatch Documentation](netwatch.md)
* [WorkPulse Documentation](workpulse.md)
* [Project README](../README.md)
