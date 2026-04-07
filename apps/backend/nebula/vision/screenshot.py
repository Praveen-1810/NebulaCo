import io
import os
import win32clipboard
from PIL import ImageGrab, Image
from pathlib import Path
from datetime import datetime
from nebula.logger import get_logger

logger = get_logger("Screenshot")

# Temp folder for internal screen reading use
TEMP_DIR = Path(os.environ.get("TEMP", "C:\\Temp")) / "nebula_screens"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Desktop folder for user screenshots
DESKTOP = Path(os.environ.get("USERPROFILE", "C:\\Users\\user")) / "Desktop"
SCREENSHOT_DIR = DESKTOP / "Nebula Screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Screenshot folder ready: {SCREENSHOT_DIR}")


def capture_screen() -> str:
    """Used internally for screen reading/summary features. Saves to temp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = TEMP_DIR / f"screen_{timestamp}.png"
    image = ImageGrab.grab()
    image.save(str(file_path))
    logger.info(f"Screen captured to temp: {file_path}")
    return str(file_path)


def take_screenshot_command() -> str:
    """
    Called when user says take a screenshot.
    Saves to Desktop/Nebula Screenshots + copies to clipboard.
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = SCREENSHOT_DIR / f"screenshot_{timestamp}.png"

        # Take screenshot
        image = ImageGrab.grab()

        # Save to Desktop folder
        image.save(str(file_path))
        logger.info(f"Screenshot saved: {file_path}")

        # Verify saved
        if file_path.exists():
            logger.info(f"Screenshot confirmed at: {file_path}")
        else:
            logger.error("Screenshot file not found after save!")

        # Copy to clipboard
        _copy_image_to_clipboard(image)
        logger.info("Screenshot copied to clipboard")

        return str(file_path)

    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return ""


def _copy_image_to_clipboard(image: Image.Image):
    """Copy PIL image to Windows clipboard."""
    output = io.BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]
    output.close()

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()