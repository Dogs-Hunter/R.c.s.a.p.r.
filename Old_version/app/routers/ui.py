"""UI router - handles web interface pages."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..dispatcher import dispatcher
from ..resources import resolve_resource_path

router = APIRouter()
templates = Jinja2Templates(directory=resolve_resource_path(settings.template_dir))


@router.get("/config")
async def get_config():
    """Get server configuration."""
    return {
        "default_timeout": settings.default_timeout,
        "max_timeout": settings.max_timeout,
        "allowed_commands": settings.allowed_commands,
        "heartbeat_interval": settings.client_heartbeat_interval
    }


@router.get("/command", response_class=HTMLResponse)
async def command_page(request: Request):
    """Command submission UI page."""
    clients = dispatcher.get_all_clients()
    return templates.TemplateResponse(
        "command_ui.html",
        {
            "request": request,
            "clients": clients,
            "allowed_commands": settings.allowed_commands
        }
    )


@router.get("/clients-ui", response_class=HTMLResponse)
async def clients_page(request: Request):
    """Client status UI page."""
    clients = dispatcher.get_all_clients()
    return templates.TemplateResponse(
        "clients_ui.html",
        {
            "request": request,
            "clients": clients
        }
    )


@router.get("/processes", response_class=HTMLResponse)
async def processes_page(request: Request):
    """Processes UI page."""
    clients = dispatcher.get_all_clients()
    return templates.TemplateResponse(
        "processes_ui.html",
        {
            "request": request,
            "clients": clients
        }
    )


@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """Index page - redirects to command page."""
    clients = dispatcher.get_all_clients()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "clients": clients,
            "allowed_commands": settings.allowed_commands
        }
    )
