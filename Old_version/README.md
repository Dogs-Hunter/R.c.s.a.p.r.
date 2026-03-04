# Remote Command Dispatch System

English | [Русский](README.ru.md)

A system for dispatching commands to remote clients via REST API and WebSocket, with real-time result collection.

## Architecture

- **REST API Layer**: Endpoints for command submission, status queries, and client management
- **WebSocket Client Bridge**: Clients connect via WebSocket to receive and execute commands
- **In-Memory Dispatcher**: Manages job queue and routes commands to connected clients
- **UI Templates**: Web interface for command submission and client status

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python run.py
```

Or with uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Connect a Client

In a separate terminal:
```bash
python client.py --client-id workstation-01 --server ws://localhost:8000/ws
```

### 4. Send Commands

- Open browser to http://localhost:8000
- Select a client and enter a command
- View results in real-time

## Windows Packaging

See `docs/windows-packaging.md` for build steps and troubleshooting.

## API Endpoints

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/clients/{client_id}/command` | Enqueue a command for a client |
| GET | `/api/commands/{job_id}` | Get status/results of a command |
| GET | `/api/clients/{client_id}/latest-command` | Get latest command result |
| GET | `/api/clients` | List all connected clients |
| POST | `/api/clients/{client_id}/interval` | Set client reporting interval |
| POST | `/api/clients/{client_id}/report-now` | Trigger immediate client report |
| GET | `/config` | Get server configuration |
| GET | `/health` | Health check |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ws` | Client WebSocket for command execution |
| `/ws/ui` | UI WebSocket for live updates (optional) |

### UI Pages

| Page | Description |
|------|-------------|
| `/` | Home page with command form |
| `/command` | Command submission interface |
| `/clients-ui` | Client status dashboard |

## WebSocket Protocol

### Client Messages

```json
// Registration
{"type": "register", "client_id": "my-client", "address": "hostname"}

// Heartbeat
{"type": "heartbeat"}

// Command Result
{"type": "command_result", "job_id": "xxx", "command": "...", "stdout": "...", "stderr": "...", "exit_code": 0}
```

### Server Messages

```json
// Execute Command
{"type": "execute", "job_id": "xxx", "command": "Get-Process"}

// Registration Confirmation
{"type": "registered", "client_id": "xxx"}

// Error
{"type": "error", "message": "..."}
```

## Command Whitelist

By default, only these commands are allowed:
- PowerShell: `Get-Process`, `Get-Service`, `Get-EventLog`, `Get-ComputerInfo`, `Get-Volume`, `Get-NetIPAddress`, `Test-Connection`
- Standard: `whoami`, `hostname`, `ipconfig`, `systeminfo`

Configure via environment variables in `.env`.

## Configuration

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Available settings:
- `RCD_HOST` - Server host (default: 0.0.0.0)
- `RCD_PORT` - Server port (default: 8000)
- `RCD_DEBUG` - Enable debug mode (default: true)
- `RCD_DEFAULT_TIMEOUT` - Default command timeout (default: 60)
- `RCD_MAX_TIMEOUT` - Maximum command timeout (default: 300)

## Testing

Run tests with pytest:

```bash
pytest tests/ -v
```

## Project Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration settings
│   ├── models.py        # Data models
│   ├── dispatcher.py    # Command dispatcher
│   └── routers/
│       ├── __init__.py
│       ├── commands.py  # Command API endpoints
│       ├── clients.py   # Client API endpoints
│       ├── websocket.py # WebSocket handlers
│       └── ui.py        # UI page routes
├── templates/
│   ├── index.html       # Home page
│   ├── command_ui.html  # Command submission UI
│   └── clients_ui.html  # Client status UI
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_dispatcher.py
│   ├── test_validation.py
│   └── test_api.py
├── client.py            # Remote client script
├── run.py               # Server run script
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## Security Considerations

1. **Command Whitelist**: All commands are validated against a whitelist
2. **Rate Limiting**: Configurable rate limits for command submission
3. **No Authentication (Baseline)**: This is a baseline implementation. Add JWT/API keys for production.
4. **In-Memory Storage**: Job state is not persisted. Consider Redis/DB for production.

