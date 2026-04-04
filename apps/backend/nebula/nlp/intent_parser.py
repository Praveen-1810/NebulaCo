from nebula.logger import get_logger
from nebula.utils.constants import INTENT_SYSTEM, INTENT_CHAT
import re

logger = get_logger("IntentParser")

# ================= APP / SYSTEM KEYWORDS =================

OPEN_WORDS = ["open", "launch", "start"]
CLOSE_WORDS = ["close", "exit", "quit", "stop"]

BACKGROUND_WORDS = ["background", "in background", "in the background"]
NEW_WORDS = ["new", "another"]

SEPARATORS = [" and ", ",", " & "]

MINIMIZE_ALL = ["minimize all", "show desktop", "take me home"]
MINIMIZE_APP = ["minimize", "hide"]

VOLUME_UP = ["volume up", "increase volume"]
VOLUME_DOWN = ["volume down", "decrease volume"]
MUTE = ["mute", "silent"]

BRIGHT_UP = ["brightness up"]
BRIGHT_DOWN = ["brightness down"]
BRIGHT_MAX = ["brightness max", "full brightness"]
BRIGHT_LOW = ["brightness low", "dim"]

# ================= FILE COMMANDS =================

FILE_SEARCH_WORDS = ["search file", "find file"]
FOLDER_SEARCH_WORDS = ["search folder", "find folder"]
OPEN_FILE_WORDS = ["open file"]
DELETE_WORDS = ["delete", "remove"]

# ================= BROWSER =================

SEARCH_WORDS = ["search", "find"]
YOUTUBE_WORDS = ["youtube"]
BROWSER_WORDS = ["chrome", "edge"]

# ================= TIME =================

TIME_WORDS = ["time", "what time", "current time"]
DATE_WORDS = ["date", "today", "what date"]
TIMER_WORDS = ["set timer", "start timer"]
ALARM_WORDS = ["set alarm"]

# ================= FOLDERS =================

KNOWN_FOLDERS = [
    "desktop", "downloads", "documents",
    "pictures", "photos", "videos", "music"
]

# ================= SCREEN =================

SCREEN_SUMMARY = [
    "summarize this page",
    "summarize the page",
    "summarize screen",
    "explain this page",
    "explain screen"
]

SCREEN_QA_TRIGGERS = [
    "what does this say",
    "what is written",
    "what is on screen",
    "what's on screen"
]

EXTRACT_TEXT_WORDS = [
    "extract text",
    "extract the text",
    "extract the words",  # BUG FIX 1 — missing comma, was concatenated with next string
    "read the page",
    "read screen text"
]


# ================= HELPERS =================

def _strip_words(text, words):
    for w in words:
        text = text.replace(w, "")
    return " ".join(text.split())

def _extract_apps(text, keywords):
    t = _strip_words(text.lower(), keywords + NEW_WORDS + BACKGROUND_WORDS)
    parts = [t]
    for s in SEPARATORS:
        parts = sum([p.split(s) for p in parts], [])
    return [p.strip() for p in parts if p.strip()]

def _extract_single(text, keywords):
    return _strip_words(text.lower(), keywords + NEW_WORDS + BACKGROUND_WORDS)

def _extract_browser(text):
    for b in BROWSER_WORDS:
        if b in text:
            return b
    return None

def _clean_search_query(text):
    t = text.lower()
    for w in SEARCH_WORDS:
        t = t.replace(w, "")
    for w in YOUTUBE_WORDS + BROWSER_WORDS:
        t = t.replace(w, "")
    t = re.sub(r"\b(in|on)\b", "", t)
    return " ".join(t.split()).strip()

def _extract_number(text):
    m = re.search(r"\d+", text)
    return int(m.group()) if m else None

def _extract_alarm_time(text):
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if not m:
        return None
    h = int(m.group(1))
    mnt = int(m.group(2)) if m.group(2) else 0
    ap = m.group(3)
    if ap == "pm" and h != 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    return h, mnt

# ================= PARSER =================

def parse_intent(text: str, lang: str) -> dict:
    t = text.lower().strip()
    logger.info(f"Parsing intent: {t}")

    # ---------- SCREEN SUMMARY ----------
    if any(w in t for w in SCREEN_SUMMARY):
        return {"intent": INTENT_SYSTEM, "action": "screen_summary"}

    # ---------- SCREEN QA ----------
    if any(w in t for w in SCREEN_QA_TRIGGERS):
        return {
            "intent": INTENT_SYSTEM,
            "action": "screen_qa",
            "question": text
        }

    # ---------- EXTRACT SCREEN TEXT ----------
    # BUG FIX 2 — moved up before generic open/search checks
    if any(w in t for w in EXTRACT_TEXT_WORDS):
        return {
            "intent": INTENT_SYSTEM,
            "action": "extract_screen_text"
        }

    # ---------- FILE SEARCH ----------
    if any(w in t for w in FILE_SEARCH_WORDS):
        name = _strip_words(t, FILE_SEARCH_WORDS)
        return {"intent": INTENT_SYSTEM, "action": "explorer_search", "query": name}

    if any(w in t for w in FOLDER_SEARCH_WORDS):
        name = _strip_words(t, FOLDER_SEARCH_WORDS)
        return {"intent": INTENT_SYSTEM, "action": "explorer_search", "query": name}

    # ---------- OPEN FOLDER ----------
    # BUG FIX 3 — moved BEFORE open file and open app checks
    # "open downloads" was being swallowed by open_app
    if any(w in t for w in OPEN_WORDS):
        for folder in KNOWN_FOLDERS:
            if folder in t:
                return {"intent": INTENT_SYSTEM, "action": "open_folder", "folder": folder}

    # ---------- OPEN FILE ----------
    # BUG FIX 4 — now also detects file extensions so "open resume.pdf" works
    if any(w in t for w in OPEN_FILE_WORDS) or (
        any(w in t for w in OPEN_WORDS) and re.search(r"\.\w{2,4}\b", t)
    ):
        name = _strip_words(t, OPEN_FILE_WORDS + OPEN_WORDS)
        return {"intent": INTENT_SYSTEM, "action": "open_file", "name": name}

    # ---------- DELETE ----------
    if any(w in t for w in DELETE_WORDS):
        if "folder" in t:
            name = _strip_words(t, DELETE_WORDS + ["folder"])
            return {"intent": INTENT_SYSTEM, "action": "delete_folder", "name": name}
        else:
            name = _strip_words(t, DELETE_WORDS + ["file"])
            return {"intent": INTENT_SYSTEM, "action": "delete_file", "name": name}

    # ---------- TIMER ----------
    if any(w in t for w in TIMER_WORDS):
        n = _extract_number(t)
        if n:
            if "minute" in t or "min" in t:
                return {"intent": INTENT_SYSTEM, "action": "set_timer", "seconds": n * 60}
            if "second" in t:
                return {"intent": INTENT_SYSTEM, "action": "set_timer", "seconds": n}

    # ---------- ALARM ----------
    if any(w in t for w in ALARM_WORDS):
        at = _extract_alarm_time(t)
        if at:
            return {"intent": INTENT_SYSTEM, "action": "set_alarm", "hour": at[0], "minute": at[1]}

    # ---------- TIME / DATE ----------
    if any(w in t for w in TIME_WORDS):
        return {"intent": INTENT_SYSTEM, "action": "get_time"}

    if any(w in t for w in DATE_WORDS):
        return {"intent": INTENT_SYSTEM, "action": "get_date"}

    # ---------- SEARCH ----------
    # BUG FIX 5 — guard against folder/app names triggering search
    if any(w in t for w in SEARCH_WORDS) and not any(f in t for f in KNOWN_FOLDERS):
        q = _clean_search_query(t)
        if "youtube" in t:
            return {"intent": INTENT_SYSTEM, "action": "youtube_search", "query": q}
        return {"intent": INTENT_SYSTEM, "action": "google_search", "query": q}

    # ---------- OPEN APP ----------
    for w in OPEN_WORDS:
        if w in t:
            return {
                "intent": INTENT_SYSTEM,
                "action": "open",
                "apps": _extract_apps(t, OPEN_WORDS),
                "new": any(n in t for n in NEW_WORDS),
                "background": any(b in t for b in BACKGROUND_WORDS),
                "browser": _extract_browser(t)
            }

    # ---------- CLOSE ----------
    for w in CLOSE_WORDS:
        if w in t:
            return {"intent": INTENT_SYSTEM, "action": "close", "app": _extract_single(t, CLOSE_WORDS)}

    # ---------- MINIMIZE ----------
    if any(m in t for m in MINIMIZE_ALL):
        return {"intent": INTENT_SYSTEM, "action": "minimize_all"}

    if any(m in t for m in MINIMIZE_APP):
        return {"intent": INTENT_SYSTEM, "action": "minimize_app", "app": _extract_single(t, MINIMIZE_APP)}

    # ---------- VOLUME ----------
    if any(v in t for v in VOLUME_UP):
        return {"intent": INTENT_SYSTEM, "action": "volume_up"}

    if any(v in t for v in VOLUME_DOWN):
        return {"intent": INTENT_SYSTEM, "action": "volume_down"}

    if any(v in t for v in MUTE):
        return {"intent": INTENT_SYSTEM, "action": "mute"}

    # ---------- BRIGHTNESS ----------
    if any(b in t for b in BRIGHT_MAX):
        return {"intent": INTENT_SYSTEM, "action": "brightness_max"}

    if any(b in t for b in BRIGHT_UP):
        return {"intent": INTENT_SYSTEM, "action": "brightness_up"}

    if any(b in t for b in BRIGHT_DOWN):
        return {"intent": INTENT_SYSTEM, "action": "brightness_down"}

    if any(b in t for b in BRIGHT_LOW):
        return {"intent": INTENT_SYSTEM, "action": "brightness_low"}

    return {"intent": INTENT_CHAT, "text": text}