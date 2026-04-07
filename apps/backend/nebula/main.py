import sys
import winreg
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


# =====================================================
# AUTO STARTUP — works for ALL users on ANY laptop
# =====================================================

def add_to_startup():
    try:
        # Only register when running as EXE, not as python script
        if not getattr(sys, 'frozen', False):
            return

        exe_path = sys.executable

        # HKEY_LOCAL_MACHINE = works for ALL users on the laptop
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "Nebula", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        logger.info("Nebula added to startup successfully")

    except PermissionError:
        # If no admin rights, fall back to current user only
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "Nebula", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            logger.info("Nebula added to startup (current user only)")
        except Exception as e:
            logger.error(f"Startup registration failed: {e}")

    except Exception as e:
        logger.error(f"Startup registration failed: {e}")


# Register on every launch
add_to_startup()


# =====================================================
# FASTAPI APP
# =====================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Nebula backend starting...")
    wake_listener.start()
    yield
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