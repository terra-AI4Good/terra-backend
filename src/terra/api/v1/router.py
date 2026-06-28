"""API v1 router — register domain routers here."""

from fastapi import APIRouter

from terra.api.v1.endpoints.agents import router as agents_router
from terra.api.v1.endpoints.auth import router as auth_router
from terra.api.v1.endpoints.chatbot import router as chatbot_router
from terra.api.v1.endpoints.documents import router as documents_router
from terra.api.v1.endpoints.health import router as health_router
from terra.api.v1.endpoints.mcp import router as mcp_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(auth_router, tags=["auth"])
router.include_router(chatbot_router, tags=["chatbot"])
router.include_router(documents_router, tags=["documents"])
router.include_router(mcp_router, tags=["mcp"])
router.include_router(agents_router, tags=["agents"])
