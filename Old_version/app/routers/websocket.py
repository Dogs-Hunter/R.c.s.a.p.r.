"""WebSocket router - handles client and UI WebSocket connections."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
import json
import logging
from datetime import datetime

from ..models import CommandResult
from ..dispatcher import dispatcher
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def client_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for remote client connections.
    
    Protocol:
    - Registration: { "type": "register", "client_id": "xxx", "address": "xxx", "user": "xxx" }
    - Commands received: { "type": "execute", "job_id": "xxx", "command": "xxx" }
    - Results sent: { "type": "command_result", "job_id": "xxx", "command": "xxx", "stdout": "xxx", "stderr": "xxx", "exit_code": 0 }
    - Heartbeat: { "type": "heartbeat" }
    """
    await websocket.accept()
    client_id = None
    
    try:
        # Wait for registration
        data = await websocket.receive_text()
        message = json.loads(data)
        
        if message.get("type") != "register":
            await websocket.send_json({"type": "error", "message": "Must register first"})
            await websocket.close()
            return
        
        client_id = message.get("client_id")
        address = message.get("address", websocket.client.host if websocket.client else "unknown")
        user = message.get("user")
        
        if not client_id:
            await websocket.send_json({"type": "error", "message": "client_id required"})
            await websocket.close()
            return
        
        # Register the client
        dispatcher.register_client(client_id, address, websocket, user=user)
        await websocket.send_json({"type": "registered", "client_id": client_id})
        logger.info(f"Client {client_id} registered from {address}")
        
        # Main message loop
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue
            
            msg_type = message.get("type")
            
            if msg_type == "heartbeat":
                # Respond to heartbeat
                await websocket.send_json({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()})
            
            elif msg_type == "command_result":
                # Process command result
                result = CommandResult(
                    timestamp=datetime.utcnow(),
                    client_id=client_id,
                    job_id=message.get("job_id"),
                    command=message.get("command", ""),
                    stdout=message.get("stdout", ""),
                    stderr=message.get("stderr", ""),
                    exit_code=message.get("exit_code", 0)
                )
                dispatcher.complete_job(result)
                await websocket.send_json({"type": "result_ack", "job_id": result.job_id})
                logger.info(f"Received result for job {result.job_id} from client {client_id}")
            
            else:
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        if client_id:
            dispatcher.unregister_client(client_id)


@router.websocket("/ws/ui")
async def ui_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for UI live updates (optional).
    
    Protocol:
    - Subscribe: { "type": "subscribe", "client_id": "xxx" }
    - Unsubscribe: { "type": "unsubscribe", "client_id": "xxx" }
    - Updates received: { "type": "job_update", "job": {...} }
    """
    await websocket.accept()
    subscriptions = set()
    
    try:
        await websocket.send_json({"type": "connected", "message": "UI WebSocket connected"})
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue
            
            msg_type = message.get("type")
            
            if msg_type == "subscribe":
                client_id = message.get("client_id")
                if client_id:
                    subscriptions.add(client_id)
                    await websocket.send_json({"type": "subscribed", "client_id": client_id})
            
            elif msg_type == "unsubscribe":
                client_id = message.get("client_id")
                if client_id:
                    subscriptions.discard(client_id)
                    await websocket.send_json({"type": "unsubscribed", "client_id": client_id})
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})
    
    except WebSocketDisconnect:
        logger.info("UI WebSocket disconnected")
    except Exception as e:
        logger.error(f"UI WebSocket error: {e}")
