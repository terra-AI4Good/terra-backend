"""Top-level API router."""

from fastapi import APIRouter

from terra.api.v1.router import router as v1_router

router = APIRouter()


@router.get("/health")
async def root_health() -> dict[str, str]:
    """Root health check — convenient for ALB/ECS health checks."""
    return {"status": "healthy"}


router.include_router(v1_router, prefix="/api/v1")
