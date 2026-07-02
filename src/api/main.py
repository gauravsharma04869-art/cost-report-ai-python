"""
FastAPI application entry point.

Creates and configures the FastAPI app with middleware, CORS, and route registrations.
Run with: uvicorn src.api.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.api.routes import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Enterprise-grade Medicare Cost Report AI backend. "
                    "Ingests unstructured healthcare financial data, performs "
                    "AI-powered GL-to-CMS cost center mapping, and exports "
                    "HFS-compatible import files.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root redirect to docs
    from fastapi.responses import RedirectResponse

    @app.get("/")
    async def root():
        return RedirectResponse(url="/docs")

    # Register API routes
    app.include_router(router)

    # Serve generated exports as static files
    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    return app


# Create the app instance for uvicorn
app = create_app()
