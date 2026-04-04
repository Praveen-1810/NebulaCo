from fastapi import FastAPI
from contextlib import asynccontextmanager

from nebula.config import APP_NAME, HOST, PORT
from nebula.logger import get_logger
from nebula.wake.wake_listener import WakeListener

from nebula.api import (
    routes_misc,
    routes_music,
    routes_system,
    routes_screen,
    routes_intent
)

logger = get_logger()
wake_listener = WakeListener()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Nebula backend starting...")
    wake_listener.start()
    yield
    # Shutdown
    logger.info("Nebula backend shutting down...")
    wake_listener.stop()


app = FastAPI(
    title=APP_NAME,
    lifespan=lifespan
)

# Register API routes
app.include_router(routes_misc.router)
app.include_router(routes_music.router)
app.include_router(routes_system.router)
app.include_router(routes_screen.router)
app.include_router(routes_intent.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=False
    )
