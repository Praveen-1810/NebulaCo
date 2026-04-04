import threading
import time
from datetime import datetime
from nebula.tts.tts_engine import speak
from nebula.logger import get_logger

logger = get_logger("TimeActions")

# ---------------- TIME / DATE ----------------

def get_time():
    return datetime.now().strftime("%I:%M %p")

def get_date():
    return datetime.now().strftime("%A, %d %B %Y")

# ---------------- TIMER ----------------

def start_timer(seconds: int):
    def timer_thread():
        logger.info(f"Timer started: {seconds}s")
        time.sleep(seconds)
        speak("Timer finished")

    threading.Thread(target=timer_thread, daemon=True).start()

# ---------------- ALARM ----------------

def set_alarm(hour: int, minute: int):
    def alarm_thread():
        logger.info(f"Alarm set for {hour}:{minute:02d}")
        while True:
            now = datetime.now()
            if now.hour == hour and now.minute == minute:
                speak("Alarm ringing")
                break
            time.sleep(10)

    threading.Thread(target=alarm_thread, daemon=True).start()
