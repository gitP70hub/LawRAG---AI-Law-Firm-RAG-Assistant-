"""Health-check router."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    service: str


@router.get("/health", response_model=HealthResponse, summary="Health Check")
async def health_check() -> HealthResponse:
    """Returns 200 OK when the service is running."""
    return HealthResponse(status="ok", version="0.1.0", service="LawRAG")
