"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from shackles.api.errors import register_exception_handlers
from shackles.api.routes import (
    accommodation as accommodation_routes,
    auth as auth_routes,
    contact as contact_routes,
    events as event_routes,
    health as health_routes,
    papers as paper_routes,
    payments as payment_routes,
    registrations as registration_routes,
    scanner as scanner_routes,
    teams as team_routes,
    users as user_routes,
)
from shackles.api.routes.admin import admin_router
from shackles.config import settings
from shackles.db.engine import engine
from shackles.services.rate_limit import limiter
from shackles.workers.queue import close_arq_pool, init_arq_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ---- Startup ----
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("[startup] Database connected")
    except Exception as exc:
        print(f"[startup] Database connection FAILED: {exc}")

    try:
        await init_arq_pool()
    except Exception as exc:
        print(f"[startup] ARQ pool init FAILED: {exc}")

    # Ensure local storage directory exists
    Path(settings.storage_local_root).mkdir(parents=True, exist_ok=True)

    print(
        f"[startup] {settings.app_name} "
        f"env={settings.environment} year={settings.active_year}"
    )

    yield

    # ---- Shutdown ----
    try:
        await close_arq_pool()
    except Exception as exc:
        print(f"[shutdown] ARQ pool close failed: {exc}")

    await engine.dispose()
    print("[shutdown] Database pool disposed")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # ---- Exception handlers ----
    register_exception_handlers(app)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ---- Rate limiter state ----
    app.state.limiter = limiter

    # ---- CORS ----
    origins = ["*"] if settings.is_development else [settings.public_app_url]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Request ID middleware ----
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    # ---- Static files (local storage) ----
    storage_dir = Path(settings.storage_local_root)
    storage_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/static",
        StaticFiles(directory=str(storage_dir)),
        name="static",
    )

    # ---- Routers ----
    app.include_router(health_routes.router, prefix="/api")
    app.include_router(auth_routes.router, prefix="/api")
    app.include_router(user_routes.router, prefix="/api")
    app.include_router(event_routes.router, prefix="/api")
    app.include_router(registration_routes.router, prefix="/api")
    app.include_router(team_routes.router, prefix="/api")
    app.include_router(paper_routes.router, prefix="/api")
    app.include_router(accommodation_routes.router, prefix="/api")
    app.include_router(contact_routes.router, prefix="/api")
    app.include_router(payment_routes.router, prefix="/api")
    app.include_router(scanner_routes.router, prefix="/api")
    app.include_router(admin_router, prefix="/api")

    # ---- Root ----
    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {
            "app": settings.app_name,
            "year": str(settings.active_year),
            "docs": "/docs",
        }

    return app


app = create_app()


def run() -> None:
    """CLI entry point for `uv run shackles`."""
    import uvicorn

    uvicorn.run(
        "shackles.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
    )