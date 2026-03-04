"""In-memory dispatcher for command execution."""
import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Optional
import logging

from .models import Job, JobStatus, CommandResult, ClientInfo

logger = logging.getLogger(__name__)


class Dispatcher:
    """Manages command dispatch to connected clients."""
    
    def __init__(self):
        # Job storage
        self._jobs: dict[str, Job] = {}
        self._client_jobs: dict[str, list[str]] = defaultdict(list)
        
        # Client connections
        self._clients: dict[str, ClientInfo] = {}
        self._client_websockets: dict[str, any] = {}  # client_id -> websocket
        
        # Command queue
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        
        # Worker task
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the dispatcher worker."""
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Dispatcher started")
    
    async def stop(self):
        """Stop the dispatcher worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Dispatcher stopped")
    
    async def _worker(self):
        """Background worker to process queued jobs."""
        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process_job(job)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    async def _process_job(self, job: Job):
        """Process a single job."""
        job.status = JobStatus.SENDING
        job.started_at = datetime.utcnow()
        
        ws = self._client_websockets.get(job.client_id)
        if not ws:
            job.status = JobStatus.ERROR
            job.stderr = "Client not connected"
            job.finished_at = datetime.utcnow()
            return
        
        try:
            # Send command to client
            import json
            message = {
                "type": "execute",
                "job_id": job.id,
                "command": job.command
            }
            await ws.send_json(message)
            job.status = JobStatus.EXECUTING
            logger.info(f"Sent command to client {job.client_id}: {job.command}")
        except Exception as e:
            job.status = JobStatus.ERROR
            job.stderr = str(e)
            job.finished_at = datetime.utcnow()
            logger.error(f"Failed to send command: {e}")
    
    def enqueue(self, job: Job) -> str:
        """Enqueue a job for processing."""
        self._jobs[job.id] = job
        self._client_jobs[job.client_id].append(job.id)
        self._queue.put_nowait(job)
        logger.info(f"Enqueued job {job.id} for client {job.client_id}")
        return job.id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self._jobs.get(job_id)
    
    def get_client_jobs(self, client_id: str) -> list[Job]:
        """Get all jobs for a client."""
        job_ids = self._client_jobs.get(client_id, [])
        return [self._jobs[jid] for jid in job_ids if jid in self._jobs]
    
    def get_latest_job(self, client_id: str) -> Optional[Job]:
        """Get the latest job for a client."""
        job_ids = self._client_jobs.get(client_id, [])
        if not job_ids:
            return None
        for job_id in reversed(job_ids):
            if job_id in self._jobs:
                return self._jobs[job_id]
        return None
    
    def complete_job(self, result: CommandResult):
        """Mark a job as complete with results."""
        job = self._jobs.get(result.job_id) if result.job_id else None
        if job:
            job.status = JobStatus.FINISHED
            job.stdout = result.stdout
            job.stderr = result.stderr
            job.exit_code = result.exit_code
            job.finished_at = datetime.utcnow()
            logger.info(f"Job {job.id} completed with exit code {result.exit_code}")

        # Update client's last result
        if result.client_id in self._clients:
            client = self._clients[result.client_id]
            if job and job.correlation_id == "process_report":
                client.last_process_report = result
            else:
                client.last_command_result = result
            client.last_report = datetime.utcnow()

    def register_client(self, client_id: str, address: str, websocket, user: Optional[str] = None) -> ClientInfo:
        """Register a connected client."""
        client = ClientInfo(client_id=client_id, address=address, user=user)
        self._clients[client_id] = client
        self._client_websockets[client_id] = websocket
        logger.info(f"Client registered: {client_id} from {address}")
        return client
    
    def unregister_client(self, client_id: str):
        """Unregister a disconnected client."""
        self._clients.pop(client_id, None)
        self._client_websockets.pop(client_id, None)
        logger.info(f"Client unregistered: {client_id}")
    
    def get_client(self, client_id: str) -> Optional[ClientInfo]:
        """Get client info by ID."""
        return self._clients.get(client_id)
    
    def get_all_clients(self) -> list[ClientInfo]:
        """Get all connected clients."""
        return list(self._clients.values())
    
    def is_client_connected(self, client_id: str) -> bool:
        """Check if a client is connected."""
        return client_id in self._client_websockets


# Global dispatcher instance
dispatcher = Dispatcher()
