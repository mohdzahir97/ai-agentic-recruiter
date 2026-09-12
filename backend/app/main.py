"""FastAPI application: middleware, exception handling, routes, startup."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.db.session import init_db

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info(
        "%s v%s started (db=%s)",
        settings.app_name,
        settings.app_version,
        settings.database_url.split("://", 1)[0],
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Phase 1 AI recruitment MVP: GenAI agents, a RAG pipeline over ChromaDB, "
        "semantic candidate-job matching, explainable scoring, and a mandatory "
        "human-in-the-loop decision step."
    ),
    lifespan=lifespan,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """One translation from domain error to HTTP response.

    Services raise `NotFoundError` / `ForbiddenError` / … and never import
    FastAPI; this is where those become status codes.
    """
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the detail, return a generic message: stack traces and driver errors
    # should not be handed to a browser.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong"})


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api": settings.api_v1_prefix,
    }
