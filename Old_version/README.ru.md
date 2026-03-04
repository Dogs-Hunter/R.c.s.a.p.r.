# Система удаленной отправки команд 

Система для отправки команд на удаленные клиенты через REST API и WebSocket, с получением результатов в реальном времени.

## Архитектура

- **REST API слой**: эндпоинты для отправки команд, запросов статуса и управления клиентами
- **WebSocket-мост для клиентов**: клиенты подключаются по WebSocket, чтобы получать и выполнять команды
- **Диспетчер в памяти**: управляет очередью задач и маршрутизирует команды подключенным клиентам
- **UI-шаблоны**: веб-интерфейс для отправки команд и просмотра статуса клиентов

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Запуск сервера

```bash
python run.py
```

Или напрямую через uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Подключение клиента

В отдельном терминале:

```bash
python client.py --client-id workstation-01 --server ws://localhost:8000/ws
```

### 4. Отправка команд

- Откройте браузер и перейдите на http://localhost:8000
- Выберите клиента и введите команду
- Смотрите результаты в реальном времени

## API-эндпоинты

### REST API

| Метод | Эндпоинт | Описание |
|--------|----------|-------------|
| POST | `/api/clients/{client_id}/command` | Поставить команду в очередь для клиента |
| GET | `/api/commands/{job_id}` | Получить статус/результаты выполнения команды |
| GET | `/api/clients/{client_id}/latest-command` | Получить результат последней команды |
| GET | `/api/clients` | Список всех подключенных клиентов |
| POST | `/api/clients/{client_id}/interval` | Задать интервал отчетности клиента |
| POST | `/api/clients/{client_id}/report-now` | Запросить немедленный отчет от клиента |
| GET | `/config` | Получить конфигурацию сервера |
| GET | `/health` | Проверка работоспособности |

### WebSocket-эндпоинты

| Эндпоинт | Описание |
|----------|-------------|
| `/ws` | Клиентский WebSocket для выполнения команд |
| `/ws/ui` | UI WebSocket для live-обновлений (опционально) |

### UI-страницы

| Страница | Описание |
|------|-------------|
| `/` | Главная страница с формой отправки команд |
| `/command` | Интерфейс отправки команд |
| `/clients-ui` | Дашборд статуса клиентов |

## Протокол WebSocket

### Сообщения клиента

```json
// Registration
{"type": "register", "client_id": "my-client", "address": "hostname"}

// Heartbeat
{"type": "heartbeat"}

// Command Result
{"type": "command_result", "job_id": "xxx", "command": "...", "stdout": "...", "stderr": "...", "exit_code": 0}
```

### Сообщения сервера

```json
// Execute Command
{"type": "execute", "job_id": "xxx", "command": "Get-Process"}

// Registration Confirmation
{"type": "registered", "client_id": "xxx"}

// Error
{"type": "error", "message": "..."}
```

## Белый список команд

По умолчанию разрешены только следующие команды:

- PowerShell: `Get-Process`, `Get-Service`, `Get-EventLog`, `Get-ComputerInfo`, `Get-Volume`, `Get-NetIPAddress`, `Test-Connection`
- Standard: `whoami`, `hostname`, `ipconfig`, `systeminfo`

Настраивается через переменные окружения в `.env`.

## Конфигурация

Создайте файл `.env` из `.env.example`:

```bash
cp .env.example .env
```

Доступные настройки:

- `RCD_HOST` - хост сервера (по умолчанию: 
- `RCD_PORT` - порт сервера (по умолчанию: 8000)0.0.0.0)
- `RCD_DEBUG` - включить debug-режим (по умолчанию: true)
- `RCD_DEFAULT_TIMEOUT` - таймаут выполнения команды по умолчанию (по умолчанию: 60)
- `RCD_MAX_TIMEOUT` - максимальный таймаут выполнения команды (по умолчанию: 300)

## Тестирование

Запуск тестов через pytest:

```bash
pytest tests/ -v
```

## Структура проекта

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

## Соображения по безопасности

1. **Белый список команд**: все команды проверяются по whitelist
2. **Rate limiting**: настраиваемые ограничения частоты отправки команд
3. **Без аутентификации (базовый вариант)**: это базовая реализация. Для production добавьте JWT/API keys.
4. **Хранение в памяти**: состояние задач не сохраняется. Для production рассмотрите Redis/БД.

