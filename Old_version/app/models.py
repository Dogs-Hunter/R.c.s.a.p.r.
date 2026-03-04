"""Data models for Remote Command Dispatch system."""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class JobStatus(str, Enum):
    QUEUED = "queued"
    SENDING = "sending"
    EXECUTING = "executing"
    FINISHED = "finished"
    TIMEOUT = "timeout"
    ERROR = "error"


class Job(BaseModel):
    """Represents a command execution job."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    command: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: JobStatus = JobStatus.QUEUED
    timeout: int = 60
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    correlation_id: Optional[str] = None


class CommandResult(BaseModel):
    """Result from client command execution."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    client_id: str
    job_id: Optional[str] = None
    command: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


class ClientInfo(BaseModel):
    """Information about a connected client."""
    client_id: str
    address: str
    user: Optional[str] = None
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_report: Optional[datetime] = None
    last_command_result: Optional[CommandResult] = None
    last_process_report: Optional[CommandResult] = None
    jobs: list[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class CommandRequest(BaseModel):
    """Request body for enqueueing a command."""
    command: str
    timeout: int = 60
    correlation_id: Optional[str] = None


class CommandRejection(BaseModel):
    """Rejection details for a blocked command."""
    reason: str
    policy: str
    command: str


class CommandResponse(BaseModel):
    """Response for command enqueue."""
    job_id: str
    status: str  # "queued" | "not_connected" | "rejected"
    rejection: Optional[CommandRejection] = None


class IntervalRequest(BaseModel):
    """Request body for setting client interval."""
    interval: int
