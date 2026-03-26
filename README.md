# DiscordTurnService

DiscordTurnService is a small FastAPI-based service that keeps a Discord client connected and executes one Discord DM turn on behalf of another system.

Its primary purpose is to let another service, such as Ask, delegate the task:

> ask this Discord user a question, wait for one reply, and return the reply or a timeout.

**Responsibility split:** Ask decides **who** should be reached and **through which channel**.
DiscordTurnService handles **how to perform a Discord turn** once a Discord recipient is known.

## Boundary contract: what this service is and is not

DiscordTurnService is a **stateless transport boundary** for directional turn exchange.

It is responsible for:

- Discord-ready recipient references (`user_id`, optional `channel_id`)
- correlation (`correlation_id`)
- transport payloads (`prompt`, `response_text`)
- operational lifecycle state (`received`, `open`, `answered`, `timed_out`, `canceled`, `processed`, `error`)
- timeout and error handling

It is intentionally **not** responsible for:

- canonical person modeling / person resolution
- intent classification
- mission/objective semantics
- policy reasoning
- answer quality grading
- autonomous planning or multi-step orchestration

If you need those capabilities, build them in an orchestrator layer that calls this service and stores higher-order semantics in a separate system of record.

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

Turn lifecycle transitions are monotonic and operational at this layer:

- `received -> open | processed | error`
- `open -> answered | timed_out | canceled | error`
- `answered -> processed`

Terminal states (`timed_out`, `canceled`, `processed`, `error`) do not transition back to active states.

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
  "status": "timed_out",
  "response_text": null,
  "user_id": 123456789012345678,
  "channel_id": 987654321098765432,
  "error": null
}
```

## Using this service outside its scope

When your scenario requires richer semantics (intent, mission context, retries, escalation, policies), keep this service as a narrow execution adapter and compose it with other systems:

1. **Ingress/orchestrator service**
   - Accept business-level requests (mission/task/intent).
   - Derive transport prompt(s) and call `POST /ask-turn`.
2. **Semantic state store**
   - Persist intent, objective progress, and workflow state in your domain model.
   - Store `correlation_id` as the join key to this transport exchange.
3. **Policy/quality layer**
   - Apply moderation, fallback logic, and answer quality checks before acting on returned text.

This separation keeps DiscordTurnService reliable and reusable while allowing other teams to iterate on business logic independently.

## How stakeholders can create value

- **Product teams**: standardize cross-channel "ask user and wait" flows by reusing this boundary rather than embedding Discord bot logic in every product.
- **Platform teams**: add observability, SLOs, and scaling around a single transport surface instead of many ad-hoc integrations.
- **Ops/compliance teams**: enforce policy and retention in upstream orchestration layers while keeping this component minimal and auditable.
- **Data teams**: join `correlation_id` with orchestration events to measure response latency, timeout rate, and downstream conversion.

## Integration shape with Ask

Ask should resolve `person -> channel binding -> discord recipient` before calling this API.
By design, DiscordTurnService accepts Discord-native fields (for example `user_id`), not a canonical `person_id`.

A reference integration example is available at:

- `examples/ask_orchestrator_discord_turn.py`

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
