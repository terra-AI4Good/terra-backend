"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from terra.api.router import router as api_router
from terra.config import get_settings
from terra.setup import discover_mcp_tools, register_all


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Application lifespan: create DB tables, discover MCP tools."""
    import terra.models  # noqa: F401
    from terra.db.base import Base
    from terra.db.session import engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Discover MCP tools (non-fatal if server unreachable)
    with suppress(Exception):
        await discover_mcp_tools()

    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register all tools, agents, and MCP servers
    register_all()

    app.include_router(api_router)

    return app
