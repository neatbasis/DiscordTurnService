# DiscordTurnService

DiscordTurnService is a small FastAPI-based service that keeps a Discord client connected and executes one Discord DM turn on behalf of another system.

Its primary purpose is to let another service, such as Ask, delegate the task:

> ask this Discord user a question, wait for one reply, and return the reply or a timeout.

## Features

- FastAPI HTTP API
- Discord DM ask-turn execution
- bounded timeout handling
- one active ask-turn per user
- structured JSON request/response contract
- readiness and health endpoints
- `src/` layout Python package structure
- container-friendly deployment

## Current scope

The current implementation is intentionally narrow:

- DM mode only
- synchronous `POST /ask-turn` request waits for answer or timeout
- one active turn per Discord user at a time

The service does **not** currently handle:

- multi-step conversations
- channel-mode asking
- persistence of in-flight turns across restart
- autonomous question generation
- answer generation / RAG

## Project structure

```text
.
├── pyproject.toml
├── README.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── src/
│   └── discord_turn_service/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   └── routes.py
│       ├── discord/
│       │   ├── __init__.py
│       │   └── runtime.py
│       └── turns/
│           ├── __init__.py
│           ├── registry.py
│           └── service.py
└── tests/
```

## Requirements

- Python 3.11+
- a Discord bot token
- a Discord bot/application able to DM the target users

## Configuration

The service consumes configuration from the process environment. The application does not load a `.env` file directly.

### Application environment

- `DISCORD_TOKEN`: Discord bot token
- `LOG_LEVEL`: Python logging level (default: `INFO`)

Use `.env.example` as documentation for expected application variables.

### Compose / launch environment

- `PORT`: host port mapping used by Docker Compose
- `APP_VERSION`: optional build-time version override used during image build

Launch-level variables are handled by Docker Compose, your shell, or your process manager rather than the FastAPI settings model.

## Installation

Install in editable mode with development dependencies:

```bash
pip install -e .[dev]
```

## Running locally

```bash
uvicorn discord_turn_service.main:app --host 0.0.0.0 --port 8000
```

Docs:

- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`

## Running with Docker Compose

Build and start:

```bash
docker compose up --build -d
```

The container listens on port `8000` internally. The host port is controlled by `docker-compose.yml` and your `.env`.

## API

### `GET /healthz`

Basic liveness check.

Example response:

```json
{"status": "ok"}
```

### `GET /readyz`

Reports whether the Discord runtime is connected and ready.

Example response:

```json
{"ready": true}
```

### `POST /ask-turn`

Ask a Discord user a question over DM and wait for one reply or timeout.

Example request:

```json
{
  "correlation_id": "ask-001",
  "user_id": 123456789012345678,
  "prompt": "What are you doing right now?",
  "timeout_seconds": 60.0,
  "mode": "dm"
}
```

Answered response:

```json
{
  "correlation_id": "ask-001",
  "status": "answered",
  "response_text": "Working on the Discord service.",
  "user_id": 123456789012345678,
  "channel_id": 987654321098765432,
  "error": null
}
```

Timeout response:

```json
{
  "correlation_id": "ask-001",
  "status": "timeout",
  "response_text": null,
  "user_id": 123456789012345678,
  "channel_id": 987654321098765432,
  "error": null
}
```

## Example curl

```bash
curl -X POST \
  'http://localhost:8000/ask-turn' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "correlation_id": "ask-001",
  "user_id": 123456789012345678,
  "prompt": "What are you doing right now?",
  "timeout_seconds": 60,
  "mode": "dm"
}'
```

## Development

Install dev dependencies:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest
```

Lint:

```bash
ruff check .
```

## Versioning

Package and API versioning are derived from Git tags via `setuptools-scm`.

For local installs from a Git checkout, the version is inferred from Git metadata.

For Docker builds, pass the version explicitly, for example:

```bash
export APP_VERSION=$(git describe --tags --exact-match | sed 's/^v//')
docker compose build
```

## License

MIT
