import threading
import re
from nebula.tts.tts_engine import speak

from nebula.logger import get_logger
from nebula.config import WAKE_REPLY
from nebula.tts.tts_engine import speak
from nebula.stt.assemblyai_engine import AssemblyAIEngine
from nebula.nlp.lang_detector import detect_language
from nebula.nlp.intent_parser import parse_intent

from nebula.actions.file_actions import (
    open_folder,
    open_file,
    delete_file,
    delete_folder,
    explorer_search
)

from nebula.actions.app_actions import (
    open_app, close_app,
    minimize_all, minimize_app,
    volume_up, volume_down, mute_volume,
    brightness_up, brightness_down,
    brightness_low, brightness_max,
    shutdown_system, restart_system
)

from nebula.actions.browser_actions import (
    open_site, google_search, youtube_search
)

from nebula.actions.time_actions import (
    get_time, get_date, start_timer, set_alarm
)

from nebula.vision.screenshot import capture_screen
from nebula.vision.screen_reader import read_text_from_image
from nebula.vision.vision_ai import (
    summarize_ai,
    answer_question,
    copy_to_clipboard
)

from nebula.utils.constants import INTENT_SYSTEM

logger = get_logger("SessionListener")


class WakeListener:

    def __init__(self):
        self.stt = AssemblyAIEngine()
        self._running = False

    def _normalize(self, text):
        return re.sub(r"[^\w\s]", "", text.lower()).strip()

    def _safe_speak(self, text):
        speak(text)

    def _session_loop(self):
        logger.info("Nebula session started")

        self._safe_speak(WAKE_REPLY)

        while self._running:

            spoken_text = self.stt.transcribe()
            if not spoken_text:
                continue

            norm = self._normalize(spoken_text)
            logger.info(f"Heard: {norm}")

            if norm in ["stop listening", "sleep", "exit"]:
                self._safe_speak("Going idle")
                self._running = False
                break

            intent = parse_intent(norm, detect_language(norm))
            logger.info(f"Intent → {intent}")

            if intent.get("intent") != INTENT_SYSTEM:
                self._safe_speak("Okay")
                continue

            action = intent.get("action")

            # ================= SCREEN SUMMARY =================
            if action == "screen_summary":

                self._safe_speak("Analyzing screen")

                path = capture_screen()
                text = read_text_from_image(path)

                if not text.strip():
                    self._safe_speak("I cannot see readable content")
                else:
                    summary = summarize_ai(text)
                    copy_to_clipboard(summary)
                    self._safe_speak(summary)

                continue

            # ================= SCREEN QA =================
            elif action == "screen_qa":

                self._safe_speak("Reading screen")

                path = capture_screen()
                text = read_text_from_image(path)

                if not text.strip():
                    self._safe_speak("I cannot see readable content")
                else:
                    answer = answer_question(text, intent.get("question"))
                    self._safe_speak(answer)

                continue

            # ================= FILE SYSTEM =================
            elif action == "open_folder":
                success, _ = open_folder(intent.get("folder"))
                self._safe_speak("Opening folder" if success else "Folder not found")

            elif action == "explorer_search":
                success = explorer_search(intent.get("query"))
                self._safe_speak("Searching in File Explorer" if success else "Search failed")

            elif action == "open_file":
                success, _ = open_file(intent.get("name"))
                self._safe_speak("Opening file" if success else "File not found")

            elif action == "delete_file":
                success, _ = delete_file(intent.get("name"))
                self._safe_speak("File moved to trash" if success else "File not found")

            elif action == "delete_folder":
                success, _ = delete_folder(intent.get("name"))
                self._safe_speak("Folder moved to trash" if success else "Folder not found")

            # ================= APPS =================
            elif action == "open":
                success = False
                for item in intent.get("apps", []):
                    if "." in item:
                        success |= open_site(item)
                    else:
                        success |= open_app(item)

                self._safe_speak("Done" if success else "Couldn't open")

            elif action == "google_search":
                google_search(intent.get("query"))
                self._safe_speak("Here you go")

            elif action == "youtube_search":
                youtube_search(intent.get("query"))
                self._safe_speak("Here you go")

            elif action == "get_time":
                self._safe_speak(f"The time is {get_time()}")

            elif action == "get_date":
                self._safe_speak(f"Today is {get_date()}")

            elif action == "set_timer":
                start_timer(intent.get("seconds"))
                self._safe_speak("Timer started")

            elif action == "set_alarm":
                set_alarm(intent.get("hour"), intent.get("minute"))
                self._safe_speak("Alarm set")

            elif action == "close":
                close_app(intent.get("app"))
                self._safe_speak("Closed")

            elif action == "minimize_all":
                minimize_all()
                self._safe_speak("Minimized everything")

            elif action == "minimize_app":
                minimize_app(intent.get("app"))
                self._safe_speak("Minimized")

            elif action == "volume_up":
                volume_up()
                self._safe_speak("Volume up")

            elif action == "volume_down":
                volume_down()
                self._safe_speak("Volume down")

            elif action == "mute":
                mute_volume()
                self._safe_speak("Muted")

            elif action == "brightness_up":
                brightness_up()
                self._safe_speak("Brightness increased")

            elif action == "brightness_down":
                brightness_down()
                self._safe_speak("Brightness decreased")

            elif action == "brightness_low":
                brightness_low()
                self._safe_speak("Brightness lowered")

            elif action == "brightness_max":
                brightness_max()
                self._safe_speak("Brightness max")

            elif action == "shutdown":
                self._safe_speak("Shutting down")
                shutdown_system()

            elif action == "restart":
                self._safe_speak("Restarting")
                restart_system()

    def start(self):
        if not self._running:
            self._running = True
            threading.Thread(
                target=self._session_loop,
                daemon=True
            ).start()

    def stop(self):
        self._running = False
