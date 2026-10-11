# DevDesk Ecosystem: Unified CLI Reference

This document serves as the master command-line reference for the **DevDesk Local Ecosystem**. It covers command syntax, flags, arguments, exit codes, and shell pipeline patterns for all three utilities:
* [`vault`](snippetvault.md) — Offline Knowledge Stash
* [`netwatch`](netwatch.md) — Port & Network Health Inspector
* [`workpulse`](workpulse.md) — Focus Tracking & Peer Orchestrator

---

## 1. Master Command Index

| Utility | Command | Description | Default Port / Scope |
|:---|:---|:---|:---|
| `vault` | `vault save` | Store a snippet from argument or stdin | Direct SQLite |
| `vault` | `vault list` | Search and display stashed snippets | Direct SQLite |
| `vault` | `vault get` | Render syntax-highlighted snippet | Direct SQLite |
| `vault` | `vault delete` | Remove a snippet by ID | Direct SQLite |
| `vault` | `vault serve` | Start background REST API daemon | Port `8765` |
| `netwatch` | `netwatch check` | Probe single port listener & owner | Direct TCP / Procfs |
| `netwatch` | `netwatch scan` | Table of all listening TCP/UDP ports | Kernel Procfs |
| `netwatch` | `netwatch ping` | Measure WAN round-trip latency | Public DNS TCP |
| `netwatch` | `netwatch serve` | Start network inspector REST API | Port `8766` |
| `workpulse` | `workpulse start` | Begin timed Pomodoro focus sprint | Live TUI / SQLite |
| `workpulse` | `workpulse status` | View active or latest session state | Direct SQLite |
| `workpulse` | `workpulse history` | List historical focus sessions | Direct SQLite |
| `workpulse` | `workpulse stats` | Aggregate focus time & analytics | Direct SQLite |
| `workpulse` | `workpulse peers` | Probe peer daemon health (:8765, :8766)| HTTP (300ms timeout)|

---

## 2. SnippetVault (`vault`) Reference

```text
Usage: vault [OPTIONS] COMMAND [ARGS]...
```

### 2.1 `vault save`
Save a code snippet, command sequence, or text block.

```bash
vault save [TITLE] [CODE] [OPTIONS]
```

* **Arguments:**
  * `TITLE` *(string, required)*: Descriptive headline or label for the snippet.
  * `CODE` *(string, optional)*: Code content. If omitted and stdin is a pipe, read from stdin automatically.
* **Options:**
  * `-l, --lang TEXT`: Syntax highlighting language (e.g. `python`, `bash`, `sql`, `json`, `rust`). *(Default: `text`)*
  * `-t, --tag TEXT`: Comma-delimited list of tags for filtering (e.g. `docker,deploy,db`). *(Default: `""`)*
  * `-s, --session TEXT`: WorkPulse session ID to link snippet with an active sprint. *(Default: `None`)*
* **Piping Mechanics:**
  ```bash
  # Piping directly from stdout
  docker inspect container_name | vault save "Container Config" --lang json --tag docker

  # Stashing terminal history
  history | tail -n 25 | vault save "Recent Git Sequence" --lang bash --tag git
  ```

---

### 2.2 `vault list`
Search, filter, and display stored snippets in a terminal table.

```bash
vault list [OPTIONS]
```

* **Options:**
  * `-t, --tag TEXT`: Filter by tag substring.
  * `-l, --lang TEXT`: Filter by exact language identifier.
  * `-s, --session TEXT`: Filter by associated WorkPulse session ID.
  * `-q, --search TEXT`: Full-text substring search matching title, tags, or code content.
  * `-n, --limit INTEGER`: Maximum snippets to display. *(Default: `20`)*

---

### 2.3 `vault get`
Inspect a specific snippet by ID with line numbers and Monokai terminal highlighting.

```bash
vault get [ID] [OPTIONS]
```

* **Arguments:**
  * `ID` *(integer, required)*: Primary key ID of the snippet.
* **Options:**
  * `--raw / --no-raw`: Output raw snippet code without styling or borders (useful for piping into clipboard or shell execution). *(Default: `--no-raw`)*

```bash
# Copy snippet code directly to clipboard on Linux
vault get 4 --raw | xclip -selection clipboard
```

---

### 2.4 `vault delete`
Delete a snippet from the database.

```bash
vault delete [ID] [OPTIONS]
```

* **Arguments:**
  * `ID` *(integer, required)*: Snippet ID to delete.
* **Options:**
  * `-y, --yes`: Skip confirmation prompt.

---

### 2.5 `vault serve`
Run the SnippetVault daemon exposing the REST API.

```bash
vault serve [OPTIONS]
```

* **Options:**
  * `--host TEXT`: Bind host. *(Default: `127.0.0.1`)*
  * `-p, --port INTEGER`: Listening TCP port. *(Default: `8765`)*
  * `--reload`: Enable development hot reload. *(Default: `False`)*

---

## 3. NetWatch (`netwatch`) Reference

```text
Usage: netwatch [OPTIONS] COMMAND [ARGS]...
```

### 3.1 Exit Codes Matrix
All `netwatch` inspection commands adhere to standardized Unix exit codes:

| Code | Status | Meaning |
|:---:|:---|:---|
| **`0`** | **Active / Success** | Port is open / Internet connection established. |
| **`1`** | **Inactive / Unreachable** | Port is closed / WAN target unreachable. |
| **`2`** | **Error** | Invalid argument, socket error, or insufficient system privileges. |

---

### 3.2 `netwatch check`
Inspect a specific port for an active TCP listener and identify the process owner.

```bash
netwatch check [PORT] [OPTIONS]
```

* **Arguments:**
  * `PORT` *(integer, required)*: Port number between `1` and `65535`.
* **Options:**
  * `-h, --host TEXT`: Target host to probe. *(Default: `127.0.0.1`)*
  * `-t, --timeout FLOAT`: Connection timeout in seconds. *(Default: `1.0`)*
  * `-q, --quiet`: Suppress visual terminal output; exit with code `0` (open) or `1` (closed).
  * `--json`: Output machine-parsable JSON envelope.

```bash
# Check if Vite dev server is running on 5173
netwatch check 5173

# CI script waiting for database
until netwatch check 5432 --quiet; do
  echo "Waiting for PostgreSQL..."
  sleep 1
done
```

---

### 3.3 `netwatch scan`
Scan all active TCP and UDP sockets on the host system.

```bash
netwatch scan [OPTIONS]
```

* **Options:**
  * `-k, --kind TEXT`: Socket protocol filter: `inet` (all IPv4/IPv6), `tcp`, or `udp`. *(Default: `inet`)*
  * `--json`: Output raw list of listeners in JSON format.

---

### 3.4 `netwatch ping`
Test public internet connectivity using a non-privileged TCP handshake against authoritative DNS.

```bash
netwatch ping [OPTIONS]
```

* **Options:**
  * `-t, --target TEXT`: Destination endpoint in `host:port` format. *(Default: `1.1.1.1:53`)*
  * `--timeout FLOAT`: Timeout in seconds. *(Default: `2.0`)*
  * `--json`: Output JSON envelope with latency.

---

### 3.5 `netwatch serve`
Start the NetWatch REST daemon.

```bash
netwatch serve [OPTIONS]
```

* **Options:**
  * `--host TEXT`: Bind host. *(Default: `127.0.0.1`)*
  * `-p, --port INTEGER`: Port number. *(Default: `8766`)*

---

## 4. WorkPulse (`workpulse`) Reference

```text
Usage: workpulse [OPTIONS] COMMAND [ARGS]...
```

### 4.1 `workpulse start`
Initiate a focused deep-work Pomodoro sprint with terminal Live countdown.

```bash
workpulse start [MINUTES] [OPTIONS]
```

* **Arguments:**
  * `MINUTES` *(integer, optional)*: Sprint duration in minutes. *(Default: `25`)*
* **Options:**
  * `-t, --tag TEXT`: Category tag for the sprint (e.g. `refactor`, `frontend`, `bugfix`). *(Default: `general`)*
  * `-n, --notes TEXT`: Contextual notes for the session. *(Default: `""`)*
* **Keyboard Controls:**
  * Press `Ctrl+C` (`SIGINT`) at any time to gracefully halt the session. WorkPulse records actual elapsed time, marks the session as `interrupted`, and commits the record to SQLite.

---

### 4.2 `workpulse status`
Display the state of the active session or the most recent completed sprint.

```bash
workpulse status [OPTIONS]
```

* **Options:**
  * `--id-only`: Print only the active/latest session ID (ideal for shell subshells).
  * `--json`: Output session data in JSON format.

```bash
# Link SnippetVault to current active WorkPulse sprint:
vault save "Auth fix" --session $(workpulse status --id-only)
```

---

### 4.3 `workpulse history`
Display recent focus sessions in a formatted table.

```bash
workpulse history [OPTIONS]
```

* **Options:**
  * `-n, --limit INTEGER`: Number of sessions to display. *(Default: `10`)*
  * `-t, --tag TEXT`: Filter history by tag substring.
  * `--json`: Output history in JSON format.

---

### 4.4 `workpulse stats`
Calculate aggregate productivity metrics across all stored sessions.

```bash
workpulse stats [OPTIONS]
```

* **Metrics Reported:**
  * Total focus sessions completed
  * Aggregate focus time (hours & minutes)
  * Completion rate percentage
  * Distribution by category tags
  * Total code snippets stashed during focus blocks

---

### 4.5 `workpulse peers`
Query the health and latency of peer DevDesk services over localhost HTTP.

```bash
workpulse peers [OPTIONS]
```

* **Options:**
  * `--json`: Output peer statuses in JSON format.

---

## 5. Shell Pipeline Recipes

### Recipe 1: Contextual Deep Work Session
```bash
# 1. Start a 45-minute sprint
workpulse start 45 --tag billing-api

# 2. In another terminal, save a SQL migration tied to this sprint
CURRENT_SPRINT=$(workpulse status --id-only)
cat migrations/001.sql | vault save "Billing schema migration" --lang sql --session "$CURRENT_SPRINT"

# 3. Verify server started on port 8080
netwatch check 8080
```

### Recipe 2: Automated Pre-Flight Check in Makefile or Shell
```bash
#!/usr/bin/env bash
set -e

echo "Verifying local ecosystem services..."
netwatch check 8765 --quiet || vault serve --port 8765 &
netwatch check 8766 --quiet || netwatch serve --port 8766 &

echo "DevDesk services ready!"
workpulse peers
```

---

## 6. Related Documentation
* [SnippetVault Deep Dive](snippetvault.md)
* [NetWatch Deep Dive](netwatch.md)
* [WorkPulse Deep Dive](workpulse.md)
* [Project README](../README.md)
