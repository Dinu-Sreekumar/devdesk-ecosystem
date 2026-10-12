# DevDesk Ecosystem: Unified CLI Reference

This document serves as the master command-line reference for the **DevDesk Local Ecosystem**. It covers exact command syntax, arguments, options, flags, exit codes, and shell pipeline recipes across all three utilities:
* [`vault`](snippetvault.md) — Offline Knowledge Stash
* [`netwatch`](netwatch.md) — Port & Network Health Inspector
* [`workpulse`](workpulse.md) — Focus Tracking & Peer Orchestrator

---

## 1. Master Command Index

| Utility | Command | Description | Default Scope / Protocol |
|:---|:---|:---|:---|
| `vault` | `vault save` | Store a snippet from argument or stdin | Direct SQLite |
| `vault` | `vault list` | Filter and list stashed snippets in a table | Direct SQLite |
| `vault` | `vault get` | Render syntax-highlighted snippet | Direct SQLite |
| `vault` | `vault search` | Substring search across title, code, and tags | Direct SQLite |
| `vault` | `vault delete` | Remove a snippet by ID | Direct SQLite |
| `vault` | `vault serve` | Start background REST API daemon | Port `8765` |
| `netwatch` | `netwatch check` | Probe single port listener & process owner | Direct TCP / Procfs |
| `netwatch` | `netwatch scan` | Scan range of listening TCP ports | Kernel Procfs |
| `netwatch` | `netwatch ping` | Measure WAN round-trip latency | Public DNS TCP |
| `netwatch` | `netwatch serve` | Start network inspector REST API | Port `8766` |
| `workpulse` | `workpulse start` | Begin timed Pomodoro focus sprint | Live TUI / SQLite |
| `workpulse` | `workpulse status` | View active or latest session state | Direct SQLite |
| `workpulse` | `workpulse stop` | Manually end active session & link snippets | Direct SQLite |
| `workpulse` | `workpulse log` | View table of historical focus sessions | Direct SQLite |
| `workpulse` | `workpulse history` | Alias for `workpulse log` | Direct SQLite |
| `workpulse` | `workpulse stats` | Aggregate focus time & productivity analytics | Direct SQLite |
| `workpulse` | `workpulse peers` | Probe peer daemon health (:8765, :8766) | HTTP (300ms timeout) |

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
* **Piping Examples:**
  ```bash
  # Piping directly from stdout
  docker inspect container_name | vault save "Container Config" --lang json --tag docker

  # Stashing terminal history (using single quotes to prevent shell history expansion)
  history | tail -n 25 | vault save 'Recent Git Sequence' --lang bash --tag git
  ```

---

### 2.2 `vault list`
Filter and display stored snippets in a formatted terminal table.

```bash
vault list [OPTIONS]
```

* **Options:**
  * `-n, --limit INTEGER`: Maximum number of snippets to display. *(Default: `20`)*
  * `-t, --tag TEXT`: Filter by tag substring.
  * `-l, --lang TEXT`: Filter by exact language identifier.
  * `-s, --session TEXT`: Filter by associated WorkPulse session ID.
  * `-q, --query, --search TEXT`: Substring search matching title, tags, or code content.

---

### 2.3 `vault get`
Inspect a specific snippet by ID with line numbers and Monokai terminal highlighting.

```bash
vault get [ID] [OPTIONS]
```

* **Arguments:**
  * `ID` *(integer, required)*: Primary key ID of the snippet.
* **Options:**
  * `-r, --raw / --no-raw`: Output raw snippet code without styling or borders (useful for piping into clipboard or shell execution). *(Default: `--no-raw`)*

```bash
# Copy snippet code directly to clipboard on Linux
vault get 1 --raw | xclip -selection clipboard
```

---

### 2.4 `vault search`
Dedicated text search command across title, code, and tags.

```bash
vault search [QUERY]
```

* **Arguments:**
  * `QUERY` *(string, required)*: Search term across title, code, and tags.

---

### 2.5 `vault delete`
Delete a snippet from the database by ID.

```bash
vault delete [ID] [OPTIONS]
```

* **Arguments:**
  * `ID` *(integer, required)*: Snippet ID to delete.
* **Options:**
  * `-y, --yes`: Skip confirmation prompt.

---

### 2.6 `vault serve`
Run the SnippetVault background REST API daemon.

```bash
vault serve [OPTIONS]
```

* **Options:**
  * `-h, --host TEXT`: Bind host address. *(Default: `127.0.0.1`)*
  * `-p, --port INTEGER`: Listening TCP port. *(Default: `8765`)*
  * `-r, --reload`: Enable auto-reload for development. *(Default: `False`)*

---

## 3. NetWatch (`netwatch`) Reference

```text
Usage: netwatch [OPTIONS] COMMAND [ARGS]...
```

### 3.1 Exit Codes Specification
All `netwatch check` and `netwatch ping` commands conform to deterministic Unix exit codes:

| Code | Status | Meaning |
|:---:|:---|:---|
| **`0`** | **Available / Success** | Port is FREE (for `check`) / Target is REACHABLE (for `ping`). |
| **`1`** | **In Use / Unreachable** | Port is IN USE (for `check`) / Target is UNREACHABLE (for `ping`). |

---

### 3.2 `netwatch check`
Inspect a specific port for an active listener and attribute the process owner.

```bash
netwatch check [PORT] [OPTIONS]
```

* **Arguments:**
  * `PORT` *(integer, required)*: Port number between `1` and `65535`.
* **Options:**
  * `-q, --quiet`: Suppress terminal output; exit with code `0` (port is free) or `1` (port is in use).
  * `--json`: Output machine-parsable JSON envelope.

```bash
# Check port 8080 visually
netwatch check 8080

# Scripted readiness check (block until port is free)
until netwatch check 8080 --quiet; do
  echo "Waiting for port 8080 to become available..."
  sleep 1
done
```

---

### 3.3 `netwatch scan`
Scan and display active listening TCP sockets in a given port range.

```bash
netwatch scan [OPTIONS]
```

* **Options:**
  * `-s, --start INTEGER`: Start port of scan range. *(Default: `3000`)*
  * `-e, --end INTEGER`: End port of scan range. *(Default: `9000`)*
  * `--json`: Output raw list of listeners in JSON format.

---

### 3.4 `netwatch ping`
Measure external internet connectivity using a non-privileged TCP handshake against authoritative DNS.

```bash
netwatch ping [OPTIONS]
```

* **Options:**
  * `-h, --host TEXT`: Target IP or hostname to ping. *(Default: `1.1.1.1`)*
  * `-p, --port INTEGER`: Target TCP port. *(Default: `53`)*
  * `-t, --timeout FLOAT`: Connection timeout in seconds. *(Default: `1.0`)*
  * `--json`: Output JSON envelope with latency.

---

### 3.5 `netwatch serve`
Start the NetWatch REST daemon.

```bash
netwatch serve [OPTIONS]
```

* **Options:**
  * `-h, --host TEXT`: Bind host address. *(Default: `127.0.0.1`)*
  * `-p, --port INTEGER`: Listening TCP port. *(Default: `8766`)*
  * `-r, --reload`: Enable auto-reload for development. *(Default: `False`)*

---

## 4. WorkPulse (`workpulse`) Reference

```text
Usage: workpulse [OPTIONS] COMMAND [ARGS]...
```

### 4.1 `workpulse start`
Initiate a focused deep-work Pomodoro sprint with terminal Live countdown.

```bash
workpulse start [TITLE] [OPTIONS]
```

* **Arguments:**
  * `TITLE` *(string, required)*: Goal or headline for this focus block.
* **Options:**
  * `-d, --duration INTEGER`: Sprint duration in minutes. *(Default: `25`)*
  * `-p, --ports TEXT`: Comma-separated dev ports to probe via NetWatch. *(Default: `"8000,3000,5173,8080"`)*
  * `-t, --tag TEXT`: Category tag for this session. *(Default: `general`)*
  * `-n, --notes TEXT`: Contextual notes for the session. *(Default: `""`)*
* **Keyboard Controls:**
  * Press `Ctrl+C` (`SIGINT`) at any time to gracefully halt the session. WorkPulse catches the signal, queries SnippetVault for code created during this block, records status as `ABORTED`, and finalizes the record in SQLite.

---

### 4.2 `workpulse status`
Display the details of the currently active session.

```bash
workpulse status [OPTIONS]
```

* **Options:**
  * `--id-only`: Print only the active session ID (or latest session ID if none active). Useful for shell scripting and subshells.
  * `--json`: Output session data in JSON format.

```bash
# Link SnippetVault to current active WorkPulse sprint:
vault save "Auth fix" --session $(workpulse status --id-only)
```

---

### 4.3 `workpulse stop`
Manually end an active session without waiting for the timer to expire.

```bash
workpulse stop [OPTIONS]
```

* **Options:**
  * `-a, --abort`: Mark session as `ABORTED` instead of `COMPLETED`.

---

### 4.4 `workpulse log` / `workpulse history`
Display recent focus sessions in a formatted table. `history` is an alias for `log`.

```bash
workpulse log [OPTIONS]
workpulse history [OPTIONS]
```

* **Options:**
  * `-n, --limit INTEGER`: Number of sessions to display. *(Default: `10`)*
  * `-t, --tag TEXT`: Filter history by tag substring.
  * `--json`: Output history in JSON format.

---

### 4.5 `workpulse stats`
Calculate aggregate productivity metrics across all stored sessions.

```bash
workpulse stats [OPTIONS]
```

* **Options:**
  * `--json`: Output statistics in JSON format.
* **Metrics Reported:**
  * Total Focus Sessions
  * Completed Sessions vs Aborted Sessions
  * Completion Rate Percentage
  * Total Focus Time (minutes & hours)
  * Total Snippets Linked from SnippetVault

---

### 4.6 `workpulse peers`
Probe the health of peer DevDesk services over localhost HTTP within a 300ms budget.

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
workpulse start "Billing API Refactor" -d 45 -t billing

# 2. In another terminal, save a SQL migration tied to this sprint
CURRENT_SPRINT=$(workpulse status --id-only)
cat migrations/001.sql | vault save "Billing schema migration" --lang sql --session "$CURRENT_SPRINT"

# 3. Verify server started on port 8080
netwatch check 8080
```

### Recipe 2: Automated Pre-Flight Check in Shell Script
```bash
#!/usr/bin/env bash
set -e

echo "Verifying local ecosystem services..."
# If port is free (exit 0), start the background daemon:
netwatch check 8765 --quiet && vault serve > /dev/null 2>&1 &
netwatch check 8766 --quiet && netwatch serve > /dev/null 2>&1 &
sleep 1

echo "DevDesk services ready!"
workpulse peers
```

---

## 6. Related Documentation
* [SnippetVault Deep Dive](snippetvault.md)
* [NetWatch Deep Dive](netwatch.md)
* [WorkPulse Deep Dive](workpulse.md)
* [Project README](../README.md)
