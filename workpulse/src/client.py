from typing import List, Optional, Dict, Any
import httpx

# Ecosystem port contracts
NETWATCH_URL = "http://127.0.0.1:8766"
SNIPPETVAULT_URL = "http://127.0.0.1:8765"
TIMEOUT_SECONDS = 0.3  # Hard 300ms budget per contract


def check_port_with_netwatch(port: int) -> Optional[Dict[str, Any]]:
    """
    Asks NetWatch if a specific port is in use.
    Returns port status dict if NetWatch is online, or None if offline/timed out.
    """
    try:
        url = f"{NETWATCH_URL}/api/v1/ports/{port}"
        response = httpx.get(url, timeout=TIMEOUT_SECONDS)
        if response.status_code == 200:
            return response.json()
    except (httpx.RequestError, httpx.TimeoutException):
        # NetWatch is offline or unvailable: fail-silent
        pass
    return None


def detect_active_dev_ports(target_ports: Optional[List[int]] = None) -> List[int]:
    """
    Scans a list of standard dev ports (8000, 3000, 5173, 8080) via NetWatch.
    Returns a list of ports that are currently active.
    """
    ports = target_ports or [8000, 3000, 5173, 8080]
    active_ports = []

    for p in ports:
        result = check_port_with_netwatch(p)
        if result and result.get("in_use"):
            active_ports.append(p)

    return active_ports


def get_session_snippets(session_id: str) -> List[Dict[str, Any]]:
    """
    Queries SnippetVault for snippets tagged with this WorkPulse session ID.
    Returns list of snippets if SnippetVault is online, or [] if offline.
    """
    try:
        url = f"{SNIPPETVAULT_URL}/api/v1/snippets"
        params = {"session_id": session_id}
        response = httpx.get(url, params=params, timeout=TIMEOUT_SECONDS)
        if response.status_code == 200:
            return response.json()
    except (httpx.RequestError, httpx.TimeoutException):
        # SnippetVault is offline: fail-silent
        pass
    return []


def is_service_online(base_url: str) -> bool:
    """
    Quick 300ms health probe to check if a peer service is currently running.
    """
    try:
        response = httpx.get(f"{base_url}/health", timeout=TIMEOUT_SECONDS)
        return response.status_code == 200
    except (httpx.RequestError, httpx.TimeoutException):
        return False