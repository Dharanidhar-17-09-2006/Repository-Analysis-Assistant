from dotenv import load_dotenv
load_dotenv()
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.repo_routes import router as repo_router
from app.services.embedder import get_model

logger = logging.getLogger(__name__)


# ----------------------------
# Lifespan manager
# Must be defined BEFORE FastAPI(lifespan=...) 
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    """
    Manages the lifecycle of the application, handling startup and shutdown tasks, including loading the embedding model. 
    If the model fails to load, the application startup is aborted. 
    Ensures the application is properly initialized and cleaned up.
    """
    logger.info("🚀 Starting server... Preloading embedding model")
    try:
        get_model()
        logger.info("✅ Embedding model loaded successfully")
    except Exception as e:
        # Crash loudly on startup rather than serving broken requests
        logger.critical(f"❌ Failed to load embedding model: {e}")
        raise RuntimeError(f"Model preload failed, aborting startup: {e}") from e

    yield  # App runs here

    # --- Shutdown ---
    logger.info("🛑 Shutting down server... Cleanup complete")


# ----------------------------
# FastAPI app (single definition)
# ----------------------------
app = FastAPI(
    lifespan=lifespan,
    title="Codebase Intelligence API",
    version="1.0.0",
    description="Semantic search and analysis over your codebase",
)


# ----------------------------
# Routes
# ----------------------------
@app.get("/", tags=["Health"])
def home():
    """
    Returns the status of the application, indicating whether it is running or not.
    """
    return {"status": "running"}


app.include_router(repo_router, prefix="/repo", tags=["Repository"])