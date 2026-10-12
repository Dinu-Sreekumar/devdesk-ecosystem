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

| Command | Exit Code `0` | Exit Code `1` |
|:---|:---|:---|
| **`netwatch check <port>`** | **Port is FREE** (Available to bind) | **Port is IN USE** (Occupied by another process) |
| **`netwatch ping`** | **Target REACHABLE** (WAN connection OK) | **Target UNREACHABLE** (Connection timed out) |

### Shell Pipeline Example:
```bash
# Block until port 8000 is free before starting dev server
until netwatch check 8000 --quiet; do
  echo "Waiting for port 8000 to be freed..."
  sleep 1
done
npm run dev
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

### `GET /api/v1/ports/{port}`
Performs a targeted inspection of a specific TCP port and returns process details.
* **Response (200 OK):**
```json
{
  "port": 8765,
  "in_use": true,
  "process": {
    "name": "vault",
    "pid": 42110,
    "user": "developer"
  }
}
```

### `GET /api/v1/scan`
Discovers all active listening TCP ports within a given port range.
* **Query Parameters:**
  * `start` (int, default `3000`): Start port of scan range.
  * `end` (int, default `9000`): End port of scan range.
* **Response (200 OK):**
```json
[
  {
    "port": 8765,
    "ip": "0.0.0.0",
    "process": {
      "name": "vault",
      "pid": 42110,
      "user": "developer"
    }
  },
  {
    "port": 8766,
    "ip": "0.0.0.0",
    "process": {
      "name": "netwatch",
      "pid": 42115,
      "user": "developer"
    }
  }
]
```

### `GET /api/v1/diagnostics`
Performs a full system network diagnosis, combining WAN ping latency with active local listeners.
* **Response (200 OK):**
```json
{
  "wan": {
    "host": "1.1.1.1",
    "port": 53,
    "reachable": true,
    "latency_ms": 14.82
  },
  "active_listeners_count": 2,
  "listeners": [
    {
      "port": 8765,
      "ip": "0.0.0.0",
      "process": {
        "name": "vault",
        "pid": 42110,
        "user": "developer"
      }
    }
  ]
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
PID=$(netwatch check 3000 --json | jq -r '.process.pid')
[ "$PID" != "null" ] && kill -15 "$PID"
```

### 5.2 Pre-Flight Deployment Hook
Verify that required dependencies (PostgreSQL on 5432 and Redis on 6379) are active before running integration test suites (if `netwatch check` returns code `0`, the port is free, meaning the service is offline):
```bash
# If port is free (exit code 0), fail fast because the service is offline
netwatch check 5432 --quiet && { echo "Postgres not running on port 5432 (port is free)!"; exit 1; }
netwatch check 6379 --quiet && { echo "Redis not running on port 6379 (port is free)!"; exit 1; }
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
