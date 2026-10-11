# WorkPulse Technical Documentation
**Utility:** `workpulse` | **Service Subsystem:** Focus Tracking & Local Peer Orchestration | **Storage:** `$XDG_DATA_HOME/devdesk/sessions.db`

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
            |   (:8765)      |   |   (:8766)      |   | (sessions.db)     |
            +----------------+   +----------------+   +-------------------+
            [Online: Link Code]  [Online: Active]     [Always Available]
            [Offline: Ignored]   [Offline: Ignored]   [Direct Disk Access]
```

### 2.1 The 300ms Fail-Silent Contract
When WorkPulse checks peer states (`workpulse peers` or during session summary reports), it uses `httpx` with an aggressive 300ms timeout:

```python
try:
    with httpx.Client(timeout=0.3) as client:
        resp = client.get(f"http://127.0.0.1:{port}/health")
        if resp.status_code == 200:
            return PeerHealth(name=name, status="online", latency_ms=...)
except (httpx.ConnectError, httpx.TimeoutException):
    pass
return PeerHealth(name=name, status="offline", latency_ms=None)
```

#### Why 300 Milliseconds?
1. **Localhost Round-Trip:** On Linux loopback (`127.0.0.1`), healthy daemon responses resolve in less than 5ms.
2. **Imperceptible UI Latency:** A 300ms network timeout is beneath human perceptual delay thresholds. If a daemon is unresponsive or stopped, the CLI returns immediately without UI lag.
3. **No Exceptions Propagated:** Network timeouts and socket connection errors are caught locally; WorkPulse never crashes due to a peer failure.

---

## 3. Storage & Session Lifecycle

WorkPulse adheres to the **POSIX XDG Base Directory Specification**, persisting session history in:
```text
$XDG_DATA_HOME/devdesk/sessions.db  (defaults to ~/.local/share/devdesk/sessions.db)
```

### 3.1 SQLite Schema & State Transitions
Persistence uses standard SQLite with Write-Ahead Logging (`PRAGMA journal_mode = WAL`):

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,                       -- Format: YYYYMMDD-xxxxxx (e.g. 20261011-8f4b12)
    tag TEXT NOT NULL DEFAULT 'general',       -- Work stream tag (e.g. "auth", "refactor")
    duration_minutes INTEGER NOT NULL,         -- Planned duration
    actual_seconds INTEGER DEFAULT 0,          -- Recorded focus time
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'active',     -- 'active' | 'completed' | 'interrupted'
    notes TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
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
 (Timer expires)             (User presses Ctrl+C)
             /                 \
            v                   v
   +-----------------+  +-----------------+
   |    COMPLETED    |  |   INTERRUPTED   |
   +-----------------+  +-----------------+
   (Actual = Planned)   (Actual = Elapsed seconds)
```

* **Graceful Interrupt Handling:** If a developer cancels a session via `Ctrl+C` (`SIGINT`), the signal is caught gracefully. WorkPulse records the exact elapsed seconds, records status as `interrupted`, and commits the record to SQLite before exiting with code `0`.

---

## 4. Rich Live Terminal Visualization

During active focus blocks, WorkPulse renders a non-flickering, terminal-adaptive dashboard using `rich.live.Live`:

```text
======================================================
  WorkPulse Active Sprint: [refactor-auth]
  Session ID: 20261011-8f4b12
======================================================

  [############################------------] 70%
  Remaining Time: 07:30 / 25:00

  Local Ecosystem Status:
  ● SnippetVault (:8765): Online (2 snippets captured)
  ● NetWatch     (:8766): Online (4 ports listening)

  Press [Ctrl+C] to pause or cancel sprint.
```

---

## 5. Developer Use Cases

### 5.1 Deep Work Pomodoro Block
Start a standard 25-minute focus session tagged with your active ticket:
```bash
workpulse start 25 --tag PROJ-104
```

### 5.2 Ecosystem Peer Diagnostics
Check whether peer microservices are listening on loopback:
```bash
workpulse peers
```
* **Output:** Formats peer status, latency, and service endpoints in a Rich table.

### 5.3 Productivity Analytics
Analyze historical deep-work metrics across your local machine:
```bash
workpulse stats
```
* **Output:** Total focus hours, completion percentage, most frequent tags, and stashed code snippets.

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
