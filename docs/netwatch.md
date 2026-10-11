# NetWatch Technical Documentation
**Utility:** `netwatch` | **Service Port:** `8766` | **Subsystem:** Port & Network Health Inspector

---

## 1. Overview & Engineering Rationale

Modern development workflows frequently suffer from network collision issues:
* A Docker container or background Vite/Webpack process retains port `3000` or `8080`, causing subsequent runs to fail with cryptic `EADDRINUSE` errors.
* Local health checks block indefinitely when an upstream service or database is unresponsive.
* Heavy tools like `netstat`, `lsof`, or `ss` require complex regex filtering and inconsistent shell flags across different Linux distributions.

**NetWatch** is a lightweight, zero-dependency, compiled network inspector and HTTP microservice. It provides deterministic port diagnostics, process owner attribution, WAN latency measurements, and machine-parsable exit codes for CI/CD and shell scripting.

---

## 2. Core Architecture & Inspection Mechanics

NetWatch does not rely on external shell wrappers like `lsof` or `netstat`. It operates natively through the Linux kernel and POSIX network abstractions:

```
+-------------------------------------------------------------+
|                      NetWatch Engine                        |
+-------------------------------------------------------------+
          |                                       |
    [TCP Socket Handshake]                 [Kernel Procfs via psutil]
          |                                       |
  socket.connect_ex()                     net_connections('inet')
  (0 = Open, Non-zero = Closed)                   |
          |                             Process Metadata Extraction
          |                             (PID, Name, Command, User)
          \___________________ ___________________/
                              V
              Consolidated PortStatus Contract
```

### 2.1 Non-Blocking TCP Handshake
To determine whether a port is listening, NetWatch attempts a low-overhead TCP three-way handshake:
```python
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(timeout)
result = sock.connect_ex((host, port))
is_open = (result == 0)
```
* If `connect_ex` returns `0`, an active listener accepted the SYN packet.
* Non-blocking socket timeouts (default `1.0s`) guarantee that scanning never hangs on dropped packets or unresponsive firewall policies.

### 2.2 Process Attribution & Permission Safety
When a port is open, NetWatch scans the Linux process table via `psutil` to map the listening socket to its owning process:
* **PID & Executable Name:** Identifies the culprit process (e.g., `node`, `postgres`, `python`).
* **Command Line & Owner:** Extracts full command-line arguments and username.
* **Access Denied Handling:** Linux kernel security prevents unprivileged users from reading `/proc/<pid>` for processes owned by other users or `root`. NetWatch safely catches `psutil.AccessDenied`, returning `[Protected/Root Process]` without crashing or requiring `sudo`.

### 2.3 WAN Health & Latency Measurement (`netwatch ping`)
Rather than relying on ICMP packets (which require raw socket capabilities `CAP_NET_RAW` or root privileges), NetWatch performs a high-precision TCP handshake against authoritative public DNS endpoints (`1.1.1.1:53` and `8.8.8.8:53`). It computes the round-trip time (RTT) in milliseconds:
```python
start = time.perf_counter()
sock.connect((target_host, 53))
latency_ms = (time.perf_counter() - start) * 1000.0
```

---

## 3. Exit Code Contract

NetWatch is purpose-built for shell scripting and CI/CD pipelines. Commands conform to strict Unix exit codes:

| Exit Code | Meaning | Example Scenario |
|:---:|:---|:---|
| **`0`** | **Success / Open / Online** | `netwatch check 8080` found an active listener; `netwatch ping` resolved WAN. |
| **`1`** | **Target Closed / Offline** | `netwatch check 8080` found no active listener; WAN handshake timed out. |
| **`2`** | **Execution Error** | Invalid port number (e.g., `999999`), network interface down, or syntax error. |

### Shell Pipeline Example:
```bash
# Block until backend service on 8000 is ready (up to 30s)
for i in {1..30}; do
  if netwatch check 8000 --quiet; then
    echo "Backend is ready!"
    break
  fi
  sleep 1
done
```

---

## 4. REST API Specification (Port 8766)

NetWatch includes an embedded FastAPI daemon mode (`netwatch serve`) allowing peer applications (such as WorkPulse) to query network state over HTTP.

### `GET /health`
* **Response (200 OK):**
```json
{
  "service": "netwatch",
  "status": "healthy",
  "version": "0.1.0"
}
```

### `GET /api/v1/ports`
Returns a comprehensive list of all active TCP/UDP listeners on the machine.
* **Query Parameters:**
  * `kind` (string, default `"inet"`): Filter socket kinds (`"inet"`, `"tcp"`, `"udp"`).
* **Response (200 OK):**
```json
[
  {
    "port": 8765,
    "is_open": true,
    "pid": 42110,
    "process_name": "vault",
    "cmdline": "vault serve --port 8765",
    "username": "developer",
    "host": "127.0.0.1"
  },
  {
    "port": 5432,
    "is_open": true,
    "pid": 1180,
    "process_name": "postgres",
    "cmdline": "/usr/lib/postgresql/16/bin/postgres",
    "username": "postgres",
    "host": "127.0.0.1"
  }
]
```

### `GET /api/v1/ports/{port}`
Performs a targeted inspection of a specific TCP port.
* **Response (200 OK):** Returns single `PortStatus` object.
* **Response (400 Bad Request):** Returned if the port is out of range (`1-65535`).

### `GET /api/v1/ping`
Tests external internet connectivity and measures round-trip latency.
* **Response (200 OK):**
```json
{
  "online": true,
  "latency_ms": 14.82,
  "target": "1.1.1.1:53"
}
```

---

## 5. Developer Use Cases

### 5.1 Kill Conflicting Process by Port
Inspect the PID blocking your development server and terminate it cleanly:
```bash
# Identify process listening on port 3000
netwatch check 3000

# Scripted process termination:
PID=$(netwatch check 3000 --json | jq -r '.pid')
[ "$PID" != "null" ] && kill -15 "$PID"
```

### 5.2 Pre-Flight Deployment Hook
Verify that required dependencies (PostgreSQL on 5432 and Redis on 6379) are reachable before running integration test suites:
```bash
netwatch check 5432 --quiet || { echo "Postgres not running!"; exit 1; }
netwatch check 6379 --quiet || { echo "Redis not running!"; exit 1; }
pytest tests/
```

### 5.3 Rich TUI Visual Inspection
Scan local development ports with styled status badges and formatted process owners:
```bash
netwatch scan
```

---

## 6. Related Documentation
* [Master CLI Reference](cli-reference.md)
* [SnippetVault Documentation](snippetvault.md)
* [WorkPulse Documentation](workpulse.md)
* [Project README](../README.md)
