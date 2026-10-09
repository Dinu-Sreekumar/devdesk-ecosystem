from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, status, Query, Response
from fastapi.responses import JSONResponse

from shared.models import (
    HealthResponse,
    ErrorEnvelope,
    ErrorDetail,
    SnippetCreate,
    SnippetResponse,
)
from snippetvault.src.database import (
    init_db,
    create_snippet,
    get_snippet,
    list_snippets,
    delete_snippet,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler: runs on server startup and shutdown.
    Ensures SQLite tables and indexes exist before accepting requests.
    """
    init_db()
    yield


# Initialize FastAPI app
app = FastAPI(
    title="SnippetVault",
    description="Local REST API for snippet knowledge store",
    version="0.1.0",
    lifespan=lifespan
)


# Helper for standard 404 error envelope
def not_found_response(snippet_id: int) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code="RESOURCE_NOT_FOUND",
            message=f"Snippet with id {snippet_id} does not exist"
        )
    )
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=envelope.model_dump())


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Returns daemon health status."""
    return HealthResponse(service="snippetvault", status="healthy", version="0.1.0")


@app.post(
    "/api/v1/snippets",
    response_model=SnippetResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Snippets"]
)
def create_snippet_endpoint(payload: SnippetCreate):
    """Creates a new snippet and returns the created record."""
    new_id = create_snippet(
        title=payload.title,
        code=payload.code,
        language=payload.language,
        tags=payload.tags,
        session_id=payload.session_id
    )
    snippet = get_snippet(new_id)
    return SnippetResponse(**snippet)


@app.get(
    "/api/v1/snippets",
    response_model=List[SnippetResponse],
    tags=["Snippets"]
)
def list_snippets_endpoint(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    language: Optional[str] = Query(None, description="Filter by language"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    q: Optional[str] = Query(None, description="Search term across title, code, and tags"),
    limit: int = Query(50, description="Max records to return", ge=1, le=100)
):
    """Lists and searches snippets with optional query filters."""
    snippets = list_snippets(
        tag=tag,
        language=language,
        session_id=session_id,
        query=q,
        limit=limit
    )
    return [SnippetResponse(**s) for s in snippets]


@app.get(
    "/api/v1/snippets/{snippet_id}",
    response_model=SnippetResponse,
    responses={404: {"model": ErrorEnvelope}},
    tags=["Snippets"]
)
def get_snippet_endpoint(snippet_id: int):
    """Retrieves a single snippet by ID."""
    snippet = get_snippet(snippet_id)
    if not snippet:
        return not_found_response(snippet_id)
    return SnippetResponse(**snippet)


@app.delete(
    "/api/v1/snippets/{snippet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorEnvelope}},
    tags=["Snippets"]
)
def delete_snippet_endpoint(snippet_id: int):
    """Deletes a snippet by ID."""
    success = delete_snippet(snippet_id)
    if not success:
        return not_found_response(snippet_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
