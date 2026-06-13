import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import auth, chat, conversations, documents, usage
from app.config import get_settings
from app.db.database import init_db
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.request_logger import RequestLoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title="Multimodal RAG API",
    description=(
        "Upload PDFs, extract text/tables/images, embed into a per-user vector store, "
        "and query with OpenAI-powered retrieval-augmented generation. "
        "Includes cost tracking, streaming, and per-user analytics."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(usage.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {
        "name": "Multimodal RAG API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "openai_configured": bool(settings.openai_api_key),
    }
