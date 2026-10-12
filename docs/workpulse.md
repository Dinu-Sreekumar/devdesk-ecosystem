# WorkPulse Technical Documentation
**Utility:** `workpulse` | **Service Subsystem:** Focus Tracking & Local Peer Orchestration | **Storage:** `$XDG_DATA_HOME/devdesk/workpulse.db`

---

## 1. Overview & Architectural Philosophy

High-velocity engineering requires uninterrupted deep work blocks and contextual awareness. Traditional developer time-trackers suffer from critical flaws:
* They require cloud accounts, third-party syncing, or web browser interfaces that trigger distraction.
* They lack developer context: they cannot detect what local development services were active or what code snippets were created during a focus sprint.
* Rigid monolithic designs break when satellite services are unavailable.

**WorkPulse** is a local-first terminal productivity engine and peer orchestrator. It manages Pomodoro-style deep work blocks with real-time terminal visuals, tracks session analytics in SQLite, and transparently queries local peer daemons (`vault` and `netwatch`) using a non-blocking, fail-silent architecture.

---

## 2. Fail-Silent Peer Client Architecture

A core architectural principle of the DevDesk ecosystem is **Decoupled Autonomy**: *WorkPulse must operate at 100% functionality even if SnippetVault and NetWatch are completely absent or offline.*

```
                       +-----------------------------+
                       |    WorkPulse Core Engine    |
                       +-----------------------------+
                                      |
                     +----------------+----------------+
                     | 300ms Timeout  | 300ms Timeout  |
                     v (Fail-Silent)  v (Fail-Silent)  v
            +----------------+   +----------------+   +-------------------+
            |  SnippetVault  |   |    NetWatch    |   | Local SQLite      |
            |   (:8765)      |   |   (:8766)      |   | (workpulse.db)    |
            +----------------+   +----------------+   +-------------------+
            [Online: Link Code]  [Online: Active]     [Always Available]
            [Offline: Ignored]   [Offline: Ignored]   [Direct Disk Access]
```

### 2.1 The 300ms Fail-Silent Contract
When WorkPulse checks peer states (`workpulse peers` or during session summary reports), it uses `httpx` with an aggressive 300ms timeout:

```python
TIMEOUT_SECONDS = 0.3  # Hard 300ms budget per contract

def is_service_online(base_url: str) -> bool:
    """Quick 300ms health probe to check if a peer service is currently running."""
    try:
        response = httpx.get(f"{base_url}/health", timeout=TIMEOUT_SECONDS)
        return response.status_code == 200
    except (httpx.RequestError, httpx.TimeoutException):
        return False
```

#### Why 300 Milliseconds?
1. **Localhost Round-Trip:** On Linux loopback (`127.0.0.1`), healthy daemon responses resolve in less than 5ms.
2. **Imperceptible UI Latency:** A 300ms network timeout is beneath human perceptual delay thresholds. If a daemon is unresponsive or stopped, the CLI returns immediately without UI lag.
3. **No Exceptions Propagated:** Network timeouts and socket connection errors are caught locally; WorkPulse never crashes due to a peer failure.

---

## 3. Storage & Session Lifecycle

WorkPulse adheres to the **POSIX XDG Base Directory Specification**, persisting session history in:
```text
$XDG_DATA_HOME/devdesk/workpulse.db  (defaults to ~/.local/share/devdesk/workpulse.db)
```

### 3.1 SQLite Schema & State Transitions
Persistence uses standard SQLite with Write-Ahead Logging (`PRAGMA journal_mode = WAL`):

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,                       -- Format: YYYYMMDD-xxxxxx (e.g. 20261011-8f4b12)
    title TEXT NOT NULL,                       -- Focus sprint title/goal
    duration_minutes INTEGER NOT NULL,         -- Planned duration
    started_at DATETIME NOT NULL,
    ended_at DATETIME DEFAULT NULL,
    status TEXT NOT NULL,                      -- 'ACTIVE' | 'COMPLETED' | 'ABORTED'
    metadata_json TEXT DEFAULT '{}'            -- Stores active_dev_ports, tag, notes, snippet_count
);
```

### 3.2 State Machine Lifecycle
```
             [ workpulse start ]
                      |
                      v
             +-----------------+
             |     ACTIVE      |  (Timer countdown running)
             +-----------------+
               /             \
 (Timer expires)             (User presses Ctrl+C / workpulse stop)
             /                 \
            v                   v
   +-----------------+  +-----------------+
   |    COMPLETED    |  |     ABORTED     |
   +-----------------+  +-----------------+
```

* **Graceful Interrupt Handling:** If a developer cancels a session via `Ctrl+C` (`SIGINT`) or `workpulse stop --abort`, the signal is caught gracefully. WorkPulse records `ended_at`, queries SnippetVault for snippets stashed during the sprint, sets status to `ABORTED`, and commits the record to SQLite before exiting cleanly.

---

## 4. Rich Live Terminal Visualization

During active focus blocks, WorkPulse renders a non-flickering, terminal-adaptive dashboard panel using `rich.live.Live` and `rich.panel.Panel`:

```text
╭─────────────────────── WorkPulse Focus Session ───────────────────────╮
│                                                                       │
│                       Focus: PROJ-104: Auth Refactor                  │
│                          Session: 20261011-8f4b12                     │
│                  Dev Server Running on port(s): 3000, 8000            │
│                                                                       │
│                                 24:45                                 │
│                                                                       │
│                      Press Ctrl+C to stop session                     │
│                                                                       │
╰───────────────────────────────────────────────────────────────────────╯
```

---

## 5. Developer Use Cases

### 5.1 Deep Work Pomodoro Block
Start a standard 25-minute focus session tagged with your active ticket:
```bash
workpulse start "PROJ-104: Auth Refactor" --duration 25 --tag auth
```

### 5.2 Ecosystem Peer Diagnostics
Check whether peer microservices are listening on loopback:
```bash
workpulse peers
```
* **Output:** Formats peer status, port, and endpoint in a Rich table.

### 5.3 Productivity Analytics
Analyze historical deep-work metrics across your local machine:
```bash
workpulse stats
```
* **Output:** Total focus sessions, completed vs aborted counts, completion rate percentage, total focus time (minutes and hours), and stashed code snippets linked.

### 5.4 Cross-Tool Context Linking
When WorkPulse and SnippetVault run together, code stashed during a sprint is automatically tagged with the active session ID:
```bash
# Vault automatically associates snippets with the active sprint
vault save "Auth JWT patch" --session $(workpulse status --id-only)
```

---

## 6. Related Documentation
* [Master CLI Reference](cli-reference.md)
* [SnippetVault Documentation](snippetvault.md)
* [NetWatch Documentation](netwatch.md)
* [Project README](../README.md)
