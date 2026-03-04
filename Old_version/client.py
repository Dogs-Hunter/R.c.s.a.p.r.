#!/usr/bin/env python3
"""
Remote Command Dispatch Client

This client connects to the dispatch server via WebSocket,
receives commands, executes them locally, and returns results.

Usage:
    python client.py --client-id <CLIENT_ID> --server <SERVER_URL>
    
Example:
    python client.py --client-id workstation-01 --server ws://localhost:8000/ws
"""

import argparse
import asyncio
import getpass
import json
import logging
import platform
import subprocess
import sys
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, TYPE_CHECKING, Callable

try:
    import websockets
except ImportError:
    print("websockets not installed. Run: pip install websockets")
    exit(1)

if TYPE_CHECKING:
    try:
        from websockets.legacy.client import WebSocketClientProtocol
    except ImportError:
        from websockets.client import WebSocketClientProtocol
else:
    WebSocketClientProtocol = Any


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

CONFIG_FILENAME = "client-config.json"
DEFAULT_WS_PORT = 8000
DEFAULT_WS_PATH = "/ws"


def get_config_directory() -> Path:
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_config_path() -> Path:
    return get_config_directory() / CONFIG_FILENAME


def get_legacy_config_path() -> Optional[Path]:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / CONFIG_FILENAME
    return None


def read_client_config(config_path: Path) -> dict:
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def write_client_config(config_path: Path, data: dict) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def load_client_config(config_path: Path) -> dict:
    if config_path.exists():
        return read_client_config(config_path)

    legacy_path = get_legacy_config_path()
    if legacy_path and legacy_path.exists():
        legacy_data = read_client_config(legacy_path)
        if legacy_data:
            write_client_config(config_path, legacy_data)
        return legacy_data
    return {}


def normalize_server_input(value: str) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if "://" in cleaned:
        if cleaned.startswith("ws://") or cleaned.startswith("wss://"):
            return cleaned
        return None
    if "/" in cleaned:
        return None

    host = cleaned
    port = DEFAULT_WS_PORT
    if ":" in cleaned:
        host_part, port_part = cleaned.rsplit(":", 1)
        if not host_part or not port_part.isdigit():
            return None
        host = host_part
        port = int(port_part)

    if not host:
        return None
    return f"ws://{host}:{port}{DEFAULT_WS_PATH}"


def load_saved_server_url(config_path: Path) -> Optional[str]:
    data = load_client_config(config_path)
    if not data:
        return None
    value = data.get("server_url")
    if isinstance(value, str):
        return value.strip() or None
    return None


def load_saved_client_id(config_path: Path) -> Optional[str]:
    data = load_client_config(config_path)
    if not data:
        return None
    value = data.get("client_id")
    if isinstance(value, str):
        return value.strip() or None
    return None


def save_client_config(config_path: Path, updates: dict) -> None:
    existing = load_client_config(config_path)
    merged = {**existing, **updates}
    write_client_config(config_path, merged)


def save_server_url(config_path: Path, server_url: str) -> None:
    save_client_config(config_path, {"server_url": server_url})


def prompt_server_url_console(default_value: Optional[str] = None) -> Optional[str]:
    prompt = "Server IP or WebSocket URL"
    if default_value:
        prompt += f" [{default_value}]"
    response = input(f"{prompt}: ").strip()
    if not response:
        return default_value
    return response


def prompt_server_url_gui(default_value: Optional[str] = None) -> Optional[str]:
    import tkinter as tk
    from tkinter import simpledialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return simpledialog.askstring(
            "Server Address",
            "Enter server IP or WebSocket URL",
            initialvalue=default_value,
            parent=root,
        )
    finally:
        root.destroy()


def prompt_server_url(default_value: Optional[str] = None) -> Optional[str]:
    try:
        return prompt_server_url_gui(default_value)
    except Exception:
        return prompt_server_url_console(default_value)


def resolve_server_url(
    cli_value: Optional[str],
    config_path: Path,
    prompt_func: Optional[Callable[[Optional[str]], Optional[str]]] = None,
) -> str:
    if cli_value:
        normalized = normalize_server_input(cli_value)
        if not normalized:
            raise ValueError("Invalid server URL provided via --server")
        return normalized

    saved_value = load_saved_server_url(config_path)
    if saved_value:
        normalized = normalize_server_input(saved_value)
        if normalized:
            return normalized

    if prompt_func is None:
        prompt_func = prompt_server_url

    while True:
        entered = prompt_func(None)
        if entered is None:
            raise SystemExit("Server URL entry cancelled.")
        normalized = normalize_server_input(entered)
        if normalized:
            return normalized
        print("Invalid server address. Examples: 192.168.0.10 or ws://host:8000/ws")


def resolve_client_id(cli_value: Optional[str], config_path: Path) -> str:
    if cli_value is not None:
        cleaned = cli_value.strip()
        if cleaned:
            return cleaned

    saved_value = load_saved_client_id(config_path)
    if saved_value:
        return saved_value

    new_id = str(uuid.uuid4())
    save_client_config(config_path, {"client_id": new_id})
    return new_id


class CommandClient:
    """WebSocket client for receiving and executing commands."""
    
    def __init__(self, client_id: str, server_url: str):
        self.client_id = client_id
        self.server_url = server_url
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.running = False
        self.heartbeat_interval = 30
    
    async def connect(self) -> bool:
        """Connect to the server and register."""
        logger.info(f"Connecting to {self.server_url}...")
        
        try:
            self.websocket = await websockets.connect(self.server_url)
            logger.info("Connected to server")
            
            # Register with the server
            await self.register()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def register(self) -> None:
        """Send registration message to the server."""
        message = {
            "type": "register",
            "client_id": self.client_id,
            "address": f"{platform.node()} ({platform.system()} {platform.release()})",
            "user": getpass.getuser()
        }
        if self.websocket:
            await self.websocket.send(json.dumps(message))
            logger.info(f"Registered as {self.client_id}")
    
    async def run(self) -> None:
        """Main client loop."""
        self.running = True
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        
        try:
            while self.running and self.websocket:
                try:
                    message = await self.websocket.recv()
                    await self.handle_message(str(message))
                except websockets.ConnectionClosed:
                    logger.warning("Connection closed by server")
                    break
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        finally:
            heartbeat_task.cancel()
            self.running = False
    
    async def heartbeat_loop(self) -> None:
        """Send periodic heartbeats to the server."""
        while self.running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if not self.websocket:
                    break
                if getattr(self.websocket, "closed", False):
                    logger.info("Heartbeat loop stopping: connection closed")
                    break
                await self.websocket.send(json.dumps({"type": "heartbeat"}))
                logger.debug("Heartbeat sent")
            except asyncio.CancelledError:
                break
            except websockets.ConnectionClosed:
                logger.info("Heartbeat loop stopping: connection closed")
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
    
    async def handle_message(self, message: str) -> None:
        """Handle incoming message from the server."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "registered":
                logger.info(f"Registration confirmed: {data.get('client_id')}")
            
            elif msg_type == "execute":
                await self.execute_command(data)
            
            elif msg_type == "heartbeat":
                logger.debug("Heartbeat acknowledged")
            
            elif msg_type == "result_ack":
                logger.debug(f"Result acknowledged for job {data.get('job_id')}")
            
            elif msg_type == "error":
                logger.warning(f"Server error: {data.get('message')}")
            
            else:
                logger.warning(f"Unknown message type: {msg_type}")
        
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
    
    async def execute_command(self, data: dict) -> None:
        """Execute a command and send the result back."""
        job_id = data.get("job_id")
        command = data.get("command", "")
        
        logger.info(f"Executing command: {command} (job: {job_id})")
        
        stdout = ""
        stderr = ""
        exit_code = -1
        
        try:
            # Determine shell based on platform
            if platform.system() == "Windows":
                # Use PowerShell for Windows
                process = await asyncio.create_subprocess_shell(
                    f'powershell -Command "{command}"',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                # Use bash for Unix-like systems
                process = await asyncio.create_subprocess_shell(
                    str(command),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout_bytes, stderr_bytes = await process.communicate()
            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
            exit_code = process.returncode if process.returncode is not None else -1
            
            logger.info(f"Command completed with exit code {exit_code}")
        
        except Exception as e:
            stderr = str(e)
            exit_code = -1
            logger.error(f"Command execution failed: {e}")
        
        # Send result back to server
        result = {
            "type": "command_result",
            "job_id": job_id,
            "command": command,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code
        }
        
        if self.websocket:
            await self.websocket.send(json.dumps(result))
            logger.info(f"Result sent for job {job_id}")
    
    async def disconnect(self) -> None:
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from server")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Remote Command Dispatch Client")
    parser.add_argument("--client-id", help="Unique client identifier")
    parser.add_argument("--server", help="Server WebSocket URL")
    parser.add_argument("--reconnect", action="store_true", help="Auto-reconnect on disconnect")
    parser.add_argument("--reconnect-delay", type=int, default=5, help="Reconnect delay in seconds")
    
    args = parser.parse_args()

    config_path = get_config_path()
    client_id = resolve_client_id(args.client_id, config_path)
    try:
        server_url = resolve_server_url(args.server, config_path)
    except ValueError as exc:
        logger.error(str(exc))
        return

    save_client_config(
        config_path,
        {
            "server_url": server_url,
            "client_id": client_id,
            "reconnect": args.reconnect,
            "reconnect_delay": args.reconnect_delay,
        },
    )

    client = CommandClient(client_id, server_url)
    
    while True:
        if await client.connect():
            try:
                await client.run()
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                await client.disconnect()
                break
        
        if not args.reconnect:
            break
        
        logger.info(f"Reconnecting in {args.reconnect_delay} seconds...")
        await asyncio.sleep(args.reconnect_delay)


if __name__ == "__main__":
    asyncio.run(main())
