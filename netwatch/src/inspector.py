import socket
import time
from typing import Dict, Any, List, Optional
import psutil


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """
    Checks if a local TCP port is accepting connections.
    Uses socket.connect_ex() which returns 0 on successful connection.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        # connect_ex returns 0 if connection succeeded (port in use)
        return s.connect_ex((host, port)) == 0


def get_port_process_info(port: int) -> Dict[str, Any]:
    """
    Finds the process name, PID, and username bound to a specific TCP port.
    Gracefully handles psutil.AccessDenied for root/system processes.
    """
    in_use = is_port_in_use(port)
    result: Dict[str, Any] = {
        "port": port,
        "in_use": in_use,
        "process": None
    }

    if not in_use:
        return result

    # Scan active system network connections for listening sockets on this port
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                if conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        result["process"] = {
                            "name": proc.name(),
                            "pid": conn.pid,
                            "user": proc.username()
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        result["process"] = {
                            "name": "unknown (permission denied)",
                            "pid": conn.pid,
                            "user": "restricted"
                        }
                break
    except psutil.AccessDenied:
        # User lacks permission to list system-wide sockets
        result["process"] = {
            "name": "restricted",
            "pid": None,
            "user": "root/system"
        }

    return result


def scan_ports(start_port: int = 3000, end_port: int = 9000) -> List[Dict[str, Any]]:
    """
    Discovers all active listening TCP ports within a given port range.
    Returns a sorted list of dictionaries with port and process details.
    """
    listeners = []
    seen_ports = set()

    try:
        for conn in psutil.net_connections(kind="tcp"):
            if conn.status == psutil.CONN_LISTEN and conn.laddr:
                port = conn.laddr.port
                if start_port <= port <= end_port and port not in seen_ports:
                    seen_ports.add(port)
                    proc_info = None

                    if conn.pid:
                        try:
                            proc = psutil.Process(conn.pid)
                            proc_info = {
                                "name": proc.name(),
                                "pid": conn.pid,
                                "user": proc.username()
                            }
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            proc_info = {
                                "name": "restricted",
                                "pid": conn.pid,
                                "user": "unknown"
                            }

                    listeners.append({
                        "port": port,
                        "ip": conn.laddr.ip,
                        "process": proc_info
                    })
    except psutil.AccessDenied:
        pass

    # Sort ascending by port number
    return sorted(listeners, key=lambda x: x["port"])


def check_wan_latency(host: str = "1.1.1.1", port: int = 53, timeout: float = 1.0) -> Dict[str, Any]:
    """
    Measures TCP handshake latency to an external IP (defaults to Cloudflare DNS 1.1.1.1:53).
    Returns latency in milliseconds or reachable=False on timeout.
    """
    start_time = time.perf_counter()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "host": host,
            "port": port,
            "reachable": True,
            "latency_ms": round(elapsed_ms, 2)
        }
    except (socket.timeout, socket.error) as err:
        return {
            "host": host,
            "port": port,
            "reachable": False,
            "latency_ms": None,
            "error": str(err)
        }