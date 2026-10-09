from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Standard Ecosystem Contracts (Health & Errors)
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """
    Standard health check response across all DevDesk services.
    Defined in Section 2 of SYSTEM_SPEC.md.
    """
    service: str
    status: str = "healthy"
    version: str = "0.1.0"


class ErrorDetail(BaseModel):
    """Inner payload of standard error responses."""
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    """
    Standard error envelope for non-2xx responses.
    Defined in Section 2 of SYSTEM_SPEC.md.
    """
    error: ErrorDetail


# ---------------------------------------------------------------------------
# SnippetVault Contracts
# ---------------------------------------------------------------------------

class SnippetCreate(BaseModel):
    """
    Request payload for POST /api/v1/snippets.
    """
    title: str = Field(..., description="Short summary or title of the snippet")
    code: str = Field(..., description="The code snippet text")
    language: str = Field(default="text", description="Language for syntax highlighting")
    tags: str = Field(default="", description="Comma-separated tags (e.g. 'python,cli')")
    session_id: Optional[str] = Field(default=None, description="Optional WorkPulse session ID")


class SnippetResponse(BaseModel):
    """
    Response payload representing a saved snippet in SQLite.
    """
    id: int
    title: str
    code: str
    language: str
    tags: str
    session_id: Optional[str] = None
    created_at: str
    updated_at: str
