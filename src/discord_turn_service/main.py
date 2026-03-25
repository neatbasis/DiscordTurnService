import logging
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI

from discord_turn_service.api.routes import router
from discord_turn_service.config import get_settings
from discord_turn_service.discord.runtime import runtime


def get_app_version() -> str:
    try:
        return version("discord-turn-service")
    except PackageNotFoundError:
        return "0.0.0"


settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Discord runtime")
    await runtime.start()
    yield
    logger.info("Stopping Discord runtime")
    await runtime.stop()


app = FastAPI(
    title="Discord Turn Service",
    version=get_app_version(),
    lifespan=lifespan,
)

app.include_router(router)
