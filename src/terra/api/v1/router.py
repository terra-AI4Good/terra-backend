"""API v1 router — register domain routers here."""

from fastapi import APIRouter

from terra.api.v1.endpoints.agents import router as agents_router
from terra.api.v1.endpoints.auth import router as auth_router
from terra.api.v1.endpoints.health import router as health_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(auth_router, tags=["auth"])
router.include_router(agents_router, tags=["agents"])
