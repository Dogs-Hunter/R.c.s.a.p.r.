"""Main FastAPI application for Remote Command Dispatch."""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .dispatcher import dispatcher
from .resources import resolve_resource_path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Templates
templates = Jinja2Templates(directory=resolve_resource_path(settings.template_dir))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Remote Command Dispatch server...")
    await dispatcher.start()
    logger.info("Dispatcher started")
    
    yield
    
    # Shutdown
    logger.info("Stopping dispatcher...")
    await dispatcher.stop()
    logger.info("Server shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Remote Command Dispatch",
    description="Send commands to remote clients via REST and WebSocket",
    version="0.1.0",
    lifespan=lifespan
)

# Mount static files
try:
    app.mount(
        "/static",
        StaticFiles(directory=resolve_resource_path(settings.static_dir)),
        name="static"
    )
except Exception:
    logger.warning(f"Static directory not found: {settings.static_dir}")

# Import routers
from .routers import commands, clients, websocket, ui

app.include_router(commands.router, prefix="/api", tags=["commands"])
app.include_router(clients.router, prefix="/api", tags=["clients"])
app.include_router(ui.router, tags=["ui"])
app.include_router(websocket.router, tags=["websocket"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
