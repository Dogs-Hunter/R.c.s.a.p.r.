"""Commands API router - handles command submission and status."""
from fastapi import APIRouter, HTTPException
from typing import Optional

from ..models import Job, JobStatus, CommandRequest, CommandResponse, CommandRejection
from ..dispatcher import dispatcher
from ..config import settings
from ..command_policy import is_command_allowed, allow_any_enabled

router = APIRouter()


@router.post("/clients/{client_id}/command", response_model=CommandResponse)
async def enqueue_command(client_id: str, request: CommandRequest):
    """
    Enqueue a command for a specific client.
    
    - **client_id**: The unique identifier of the target client
    - **command**: The command to execute (must be in whitelist)
    - **timeout**: Maximum execution time in seconds (default: 60)
    - **correlation_id**: Optional correlation ID for tracking
    """
    allow_any = allow_any_enabled(settings)
    allowed, normalized_command = is_command_allowed(
        request.command,
        settings.allowed_commands,
        allow_any,
    )

    # Validate command against allowlist
    if not allowed:
        reason = "allowlist" if normalized_command else "empty"
        return CommandResponse(
            job_id="",
            status="rejected",
            rejection=CommandRejection(
                reason=reason,
                policy=settings.command_policy,
                command=normalized_command,
            ),
        )
    
    # Check if client is connected
    if not dispatcher.is_client_connected(client_id):
        return CommandResponse(
            job_id="",
            status="not_connected"
        )
    
    # Create and enqueue the job
    job = Job(
        client_id=client_id,
        command=request.command,
        timeout=min(request.timeout, settings.max_timeout),
        correlation_id=request.correlation_id
    )
    
    job_id = dispatcher.enqueue(job)
    
    return CommandResponse(
        job_id=job_id,
        status="queued"
    )


@router.get("/commands/{job_id}", response_model=Job)
async def get_command_status(job_id: str):
    """
    Get the status and results of a specific command job.
    
    - **job_id**: The unique identifier of the job
    """
    job = dispatcher.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/clients/{client_id}/latest-command")
async def get_latest_command(client_id: str):
    """
    Get the latest command result for a specific client.
    Fallback endpoint for UI compatibility.
    
    - **client_id**: The unique identifier of the client
    """
    client = dispatcher.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    latest_job = dispatcher.get_latest_job(client_id)
    
    return {
        "client_id": client_id,
        "last_command_result": client.last_command_result.model_dump() if client.last_command_result else None,
        "latest_job": latest_job.model_dump() if latest_job else None
    }


