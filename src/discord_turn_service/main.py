import logging
from contextlib import asynccontextmanager
from importlib.metadata import version, PackageNotFoundError

from fastapi import FastAPI

from discord_turn_service.api.routes import router
from discord_turn_service.config import settings
from discord_turn_service.discord.runtime import runtime


def get_app_version() -> str:
    try:
        return version("discord-turn-service")
    except PackageNotFoundError:
        return "0.0.0"


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
