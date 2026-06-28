from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/system", tags=["system"])


class SystemStatusResponse(BaseModel):
    status: str
    message: str
    checkedAt: datetime


@router.get("/status", response_model=SystemStatusResponse)
def get_status() -> SystemStatusResponse:
    return SystemStatusResponse(
        status="RUNNING",
        message="MOFA AI agent server is ready",
        checkedAt=datetime.now(timezone.utc),
    )

