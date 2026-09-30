# Technical Specification: DevDesk Local Ecosystem
**Status:** Approved | **Platform:** Linux (Fedora / POSIX) | **Runtime:** Python 3.12+

---

## 1. System Overview

DevDesk is a developer tooling suite consisting of three decoupled, single-binary CLI utilities that operate independently or collaboratively via localhost HTTP contracts.

```
                      +-----------------------------+
                      |         WorkPulse           |
                      |   (Focus & Task Tracker)    |
                      +--------------+--------------+
                                     |
              +----------------------+----------------------+
              | (Optional GET: 300ms)                       | (Optional GET: 300ms)
              v                                             v
+-----------------------------+               +-----------------------------+
|        SnippetVault         |               |          NetWatch           |
|  (Local Snippet Store & API)|               |    (Port & Socket Daemon)   |
|      127.0.0.1:8765         |               |       127.0.0.1:8766        |
+-----------------------------+               +-----------------------------+
```

### Core Design Rules
1. **Zero Hard Dependencies:** Each tool must execute all core features without any peer service running.
2. **Network Budget:** All inter-tool HTTP calls use `127.0.0.1`, a hard timeout of `300ms`, and must fail silently to offline mode on any connection error (`ECONNREFUSED`, `ETIMEDOUT`, non-2xx).
3. **Filesystem Standards:** Adhere to the XDG Base Directory Specification:
   - Data / SQLite DBs: `$XDG_DATA_HOME/devdesk` (defaults to `~/.local/share/devdesk/`)
   - Configuration: `$XDG_CONFIG_HOME/devdesk` (defaults to `~/.config/devdesk/`)
   - Logs & Runtime: `$XDG_STATE_HOME/devdesk` (defaults to `~/.local/state/devdesk/`)

---

## 2. Shared Protocol & Schema Definitions

All inter-tool exchange uses JSON (`Content-Type: application/json`).

### Standard Health Response
Used by SnippetVault (`:8765/health`) and NetWatch (`:8766/health`):
```json
{
  "service": "snippetvault",
  "status": "healthy",
  "version": "0.1.0"
}
```

### Standard Error Envelope
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Snippet with id 42 does not exist",
    "details": {}
  }
}
```

---

## 3. Tool Specifications

### 3.1 SnippetVault (`vault`)
A local-first code snippet stash, searchable by language, tag, or session identifier. Operates directly against SQLite in CLI mode, or exposes a FastAPI daemon.

* **Default Daemon Port:** `127.0.0.1:8765`
* **Storage:** `$XDG_DATA_HOME/devdesk/snippets.db`

#### Database Schema (SQLite)
```sql
CREATE TABLE IF NOT EXISTS snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    code TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'text',
    tags TEXT NOT NULL DEFAULT '',           -- Comma-delimited: "python,cli,auth"
    session_id TEXT DEFAULT NULL,             -- Associated WorkPulse session
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_snippets_session ON snippets(session_id);
CREATE INDEX IF NOT EXISTS idx_snippets_language ON snippets(language);
```

#### CLI Interface
```bash
vault save "title" [code] [--lang python] [--tag api,db] [--session ID]
cat main.py | vault save "Script pipeline" --lang python
vault list [--limit 20] [--tag api] [--session ID]
vault get <id> [--copy]                      # Optionally copy to clipboard
vault search <query>                         # Substring search in title, tags, and code
vault delete <id> [--yes]
vault serve [--port 8765] [--host 127.0.0.1] # Run background HTTP server
```

#### HTTP Endpoints
| Method | Path | Query Params | Body | Success Status | Description |
|---|---|---|---|---|---|
| `GET` | `/health` | - | - | `200 OK` | Service health status |
| `POST` | `/api/v1/snippets` | - | `{ title, code, language?, tags?, session_id? }` | `201 Created` | Create snippet |
| `GET` | `/api/v1/snippets` | `tag`, `language`, `session_id`, `q`, `limit` | - | `200 OK` | List / search snippets |
| `GET` | `/api/v1/snippets/{id}` | - | - | `200 OK` / `404` | Get snippet by ID |
| `DELETE` | `/api/v1/snippets/{id}` | - | - | `204 No Content` / `404` | Delete snippet |

---

### 3.2 NetWatch (`netwatch`)
Local network and port diagnostics tool. Diagnoses listening ports, finds process collisions, and monitors dev servers.

* **Default Daemon Port:** `127.0.0.1:8766`
* **Runtime Dependencies:** `socket`, `psutil`

#### CLI Interface
```bash
netwatch check <port>                        # Inspect single port (returns PID, process name)
netwatch scan [--start 3000] [--end 9000]    # List all active listening ports in range
netwatch ping [--host 1.1.1.1]               # Check gateway/WAN latency
netwatch serve [--port 8766]                 # Launch background daemon
```

#### CLI Output & Exit Codes
- Exit code `0`: Port is free / host reachable.
- Exit code `1`: Port in use / conflict detected / host unreachable.
- Exit code `2`: Permission denied (e.g., inspecting privileged root sockets).

#### HTTP Endpoints (When running in daemon mode)
| Method | Path | Body | Success | Description |
|---|---|---|---|---|
| `GET` | `/health` | - | `200 OK` | Daemon health check |
| `GET` | `/api/v1/ports/{port}` | - | `200 OK` | Check if port is bound; returns process info |
| `GET` | `/api/v1/scan` | - | `200 OK` | Returns JSON list of all active TCP listeners |

*Example Response (`GET /api/v1/ports/8000`):*
```json
{
  "port": 8000,
  "in_use": true,
  "process": {
    "name": "python3",
    "pid": 24190,
    "user": "developer"
  }
}
```

---

### 3.3 WorkPulse (`workpulse`)
Focus session tracker and terminal timer using Rich. Enriches focus sessions with contextual data from NetWatch and SnippetVault.

* **Storage:** `$XDG_DATA_HOME/devdesk/workpulse.db`

#### Database Schema (SQLite)
```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,                     -- UUID or slug: "20261001-api-refactor"
    title TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    started_at DATETIME NOT NULL,
    ended_at DATETIME DEFAULT NULL,
    status TEXT NOT NULL,                    -- "ACTIVE", "COMPLETED", "ABORTED"
    metadata_json TEXT DEFAULT '{}'          -- Stores detected dev servers, snippet counts
);
```

#### CLI Interface
```bash
workpulse start "API Refactoring" [--duration 25] [--ports 3000,8000,5173]
workpulse status                             # Show active timer status
workpulse stop [--abort]                     # Stop session, aggregate peer data
workpulse log [--limit 10]                   # Table view of past sessions
```

#### Peer Integration Logic (Fail-Silent)
1. **On `workpulse start`:**
   - Asynchronously probe `GET http://127.0.0.1:8766/api/v1/ports/{port}` for each target port (default: `8000, 3000, 5173, 8080`) with `timeout=0.3`.
   - If active ports are found, record them in `metadata_json` (e.g., `{"active_dev_ports": [8000]}`).
   - If NetWatch is offline, proceed immediately without warnings.

2. **On `workpulse stop`:**
   - Probe `GET http://127.0.0.1:8765/api/v1/snippets?session_id={current_session_id}` with `timeout=0.3`.
   - If snippets were created during this session, print their IDs and titles in the completion summary and store count in `metadata_json`.
   - If SnippetVault is offline, complete session logging normally.

---

## 4. Repository Structure & Packaging

```text
devdesk-ecosystem/
├── .gitignore
├── README.md
├── SYSTEM_SPEC.md
├── DEVLOG.md
├── Makefile
├── shared/                     # Pure Python schema definitions & helpers
│   ├── pyproject.toml
│   └── src/
│       └── shared/
│           ├── __init__.py
│           ├── config.py       # XDG path resolvers
│           └── models.py       # Shared Pydantic data schemas
├── snippetvault/
│   ├── pyproject.toml
│   └── src/
│       └── snippetvault/
│           ├── __init__.py
│           ├── cli.py          # Typer application
│           ├── database.py     # SQLite persistence
│           └── server.py       # FastAPI application
├── netwatch/
│   ├── pyproject.toml
│   └── src/
│       └── netwatch/
│           ├── __init__.py
│           ├── cli.py
│           ├── inspector.py    # psutil / socket checks
│           └── server.py
└── workpulse/
    ├── pyproject.toml
    └── src/
        └── workpulse/
            ├── __init__.py
            ├── cli.py
            ├── timer.py        # Rich terminal display
            ├── storage.py      # SQLite session store
            └── client.py       # HTTP client with 300ms budget
```

### Dependency & Build Strategy
- **Development:** Editable installs via `pip install -e ./shared -e ./snippetvault -e ./netwatch -e ./workpulse`.
- **Distribution:** Standalone ELF binaries compiled via `pyinstaller --onefile`. Default data directories must use XDG paths so compiled binaries do not attempt to write into read-only mount points.

---

## 5. Implementation Sequence

### Phase 1: SnippetVault Core
1. Shared XDG configuration resolver (`shared/src/shared/config.py`).
2. SQLite schema initialization and CRUD unit operations (`snippetvault/src/snippetvault/database.py`).
3. CLI commands for direct database interaction (`vault save`, `vault list`, `vault get`).

### Phase 2: SnippetVault API & Remote Mode
1. FastAPI app definition exposing CRUD routes.
2. CLI flag/mode allowing commands to target either local SQLite or a running HTTP daemon.

### Phase 3: NetWatch Socket Diagnostics
1. Raw `socket` connectivity test and `psutil` listener inspection.
2. CLI interface (`netwatch check`, `netwatch scan`).
3. Daemon server mode (`netwatch serve`).

### Phase 4: WorkPulse & Integration
1. SQLite session store and Rich live timer interface.
2. Resilient HTTP peer client (`httpx` with 300ms circuit-breaker behavior).
3. Session enrichment hooks.

### Phase 5: Packaging & Binary Verification
1. PyInstaller spec files for `vault`, `netwatch`, and `workpulse`.
2. Clean environment test on a minimal Linux VM without Python installed.