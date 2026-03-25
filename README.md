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
