from PIL import ImageGrab
from pathlib import Path
from datetime import datetime
from nebula.logger import get_logger

logger = get_logger("Screenshot")

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def capture_screen() -> str:
    """
    Captures the full screen and saves it to /screenshots
    Returns the file path.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = SCREENSHOT_DIR / f"screen_{timestamp}.png"

    image = ImageGrab.grab()
    image.save(file_path)

    logger.info(f"Screenshot saved: {file_path}")
    return str(file_path)
