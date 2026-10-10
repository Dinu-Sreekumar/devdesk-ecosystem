from typing import List, Dict, Any
from fastapi import FastAPI, Query

from shared.models import (
    HealthResponse,
    PortStatusResponse,
    DiagnosticsResponse,
)
from netwatch.src.inspector import (
    get_port_process_info,
    scan_ports,
    check_wan_latency,
)

app = FastAPI(
    title="NetWatch",
    description="Local port and network health inspector daemon",
    version="0.1.0"
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Returns NetWatch daemon health status."""
    return HealthResponse(service="netwatch", status="healthy", version="0.1.0")


@app.get("/api/v1/ports/{port}", response_model=PortStatusResponse, tags=["Diagnostics"])
def check_port_endpoint(port: int):
    """
    Checks if a specific port is in use and returns process info if bound.
    Queried by WorkPulse on session start.
    """
    info = get_port_process_info(port)
    return PortStatusResponse(**info)


@app.get("/api/v1/scan", tags=["Diagnostics"])
def scan_ports_endpoint(
    start: int = Query(3000, description="Start port range"),
    end: int = Query(9000, description="End port range")
):
    """Returns all active listening TCP ports in the range."""
    return scan_ports(start_port=start, end_port=end)


@app.get("/api/v1/diagnostics", response_model=DiagnosticsResponse, tags=["Diagnostics"])
def diagnostics_endpoint():
    """Full system network diagnosis: WAN ping and active listeners."""
    wan = check_wan_latency()
    listeners = scan_ports(start_port=1000, end_port=9000)
    return DiagnosticsResponse(
        wan=wan,
        active_listeners_count=len(listeners),
        listeners=listeners
    )