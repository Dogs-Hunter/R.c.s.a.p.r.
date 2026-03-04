"""Clients API router - handles client management."""
from fastapi import APIRouter, HTTPException
from typing import Optional

from ..models import ClientInfo, IntervalRequest
from ..dispatcher import dispatcher

router = APIRouter()


@router.get("/clients")
async def list_clients():
    """
    Get a list of all connected clients.
    """
    clients = dispatcher.get_all_clients()
    return {
        "clients": [
            {
                "client_id": c.client_id,
                "address": c.address,
                "user": c.user,
                "connected_at": c.connected_at.isoformat(),
                "last_report": c.last_report.isoformat() if c.last_report else None,
                "last_process_report": c.last_process_report.model_dump() if c.last_process_report else None,
                "jobs_count": len(c.jobs)
            }
            for c in clients
        ],
        "total": len(clients)
    }


@router.get("/clients/{client_id}")
async def get_client(client_id: str):
    """
    Get information about a specific client.
    
    - **client_id**: The unique identifier of the client
    """
    client = dispatcher.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {
        "client_id": client.client_id,
        "address": client.address,
        "user": client.user,
        "connected_at": client.connected_at.isoformat(),
        "last_report": client.last_report.isoformat() if client.last_report else None,
        "last_command_result": client.last_command_result.model_dump() if client.last_command_result else None,
        "last_process_report": client.last_process_report.model_dump() if client.last_process_report else None,
        "jobs": client.jobs
    }


@router.post("/clients/{client_id}/interval")
async def set_client_interval(client_id: str, request: IntervalRequest):
    """
    Set the reporting interval for a specific client.
    
    - **client_id**: The unique identifier of the client
    - **interval**: The new interval in seconds
    """
    client = dispatcher.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # In a full implementation, this would send a message to the client
    # For now, we just acknowledge the request
    return {
        "client_id": client_id,
        "interval": request.interval,
        "status": "configured"
    }


@router.post("/clients/{client_id}/report-now")
async def trigger_client_report(client_id: str):
    """
    Trigger an immediate report from a specific client.
    
    - **client_id**: The unique identifier of the client
    """
    client = dispatcher.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # In a full implementation, this would send a message to the client
    # For now, we just acknowledge the request
    return {
        "client_id": client_id,
        "status": "report_requested"
    }
