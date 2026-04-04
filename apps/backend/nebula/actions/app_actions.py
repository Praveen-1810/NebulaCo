#app actions
import os
import subprocess
import ctypes
import time
import psutil
import json
from pathlib import Path

import win32gui
import win32process
import pythoncom
import wmi

from nebula.logger import get_logger
logger = get_logger("AppActions")

# ==================================================
# APP REGISTRY
# ==================================================

APP_INDEX = {}

APP_ALIASES = {
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "files": "explorer",
    "file explorer": "explorer",
}

# ==================================================
# BUILD INDEX
# ==================================================

def _build_app_index():
    start_dirs = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
    ]

    for d in start_dirs:
        if d.exists():
            for i in d.rglob("*.lnk"):
                APP_INDEX[i.stem.lower()] = str(i)

    result = subprocess.run(
        ["powershell", "-Command", "Get-StartApps | ConvertTo-Json"],
        capture_output=True, text=True, shell=True
    )

    if result.stdout:
        try:
            for app in json.loads(result.stdout):
                APP_INDEX[app["Name"].lower()] = f"uwp:{app['AppID']}"
        except Exception:
            pass

    # Explicit apps (DO NOT os.startfile these)
    APP_INDEX.update({
        "explorer": "explorer.exe",
        "chrome": "chrome",
        "code": "code",
    })

_build_app_index()

# ==================================================
# HELPERS
# ==================================================

def _resolve_alias(app: str) -> str:
    return APP_ALIASES.get(app.lower(), app.lower())


def _focus_existing(app: str) -> bool:
    found = False

    def handler(hwnd, _):
        nonlocal found
        if not win32gui.IsWindowVisible(hwnd):
            return True

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        for p in psutil.process_iter(["pid", "name"]):
            if p.info["pid"] == pid and app in (p.info["name"] or "").lower():
                win32gui.ShowWindow(hwnd, 9)
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass
                found = True
                return False
        return True

    try:
        win32gui.EnumWindows(handler, None)
    except Exception:
        pass

    return found


def _launch(target: str, new=False, background=False) -> bool:
    try:
        # UWP app
        if target.startswith("uwp:"):
            subprocess.run(
                ["explorer.exe", f"shell:AppsFolder\\{target[4:]}"],
                shell=True
            )
            return True

        # Chrome
        if target == "chrome":
            args = ["chrome"]
            if new:
                args.append("--new-window")
            subprocess.Popen(
                args,
                creationflags=0x08000000 if background else 0
            )
            return True

        # VS Code
        if target == "code":
            subprocess.Popen(
                ["code", "-n"] if new else ["code"],
                creationflags=0x08000000 if background else 0
            )
            return True

        # Real executable or shortcut only
        if target.endswith(".exe") or target.endswith(".lnk"):
            os.startfile(target)
            return True

    except Exception as e:
        logger.error(f"Launch failed: {e}")

    return False

# ==================================================
# ACTIONS
# ==================================================

def open_app(app: str, new=False, background=False) -> bool:
    app = _resolve_alias(app)
    logger.info(f"Open app request: {app}, new={new}, bg={background}")

    # Focus existing
    if not new and _focus_existing(app):
        return True

    # Launch new
    for name, target in APP_INDEX.items():
        if app == name or app in name:
            return _launch(target, new, background)

    logger.warning(f"App not found: {app}")
    return False


def close_app(app: str) -> bool:
    app = _resolve_alias(app)
    for p in psutil.process_iter(["name"]):
        if p.info["name"] and app in p.info["name"].lower():
            p.terminate()
    return True


def minimize_all():
    ctypes.windll.user32.keybd_event(0x5B,0,0,0)
    ctypes.windll.user32.keybd_event(0x44,0,0,0)
    ctypes.windll.user32.keybd_event(0x44,0,2,0)
    ctypes.windll.user32.keybd_event(0x5B,0,2,0)


def minimize_app(app: str):
    app = _resolve_alias(app)

    def handler(hwnd, _):
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        for p in psutil.process_iter(["pid","name"]):
            if p.info["pid"] == pid and app in (p.info["name"] or "").lower():
                win32gui.ShowWindow(hwnd, 6)
                return False
        return True

    try:
        win32gui.EnumWindows(handler, None)
    except Exception:
        pass

    return True


# ==================================================
# VOLUME
# ==================================================

VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_MUTE = 0xAD

def _press(k, n=1):
    for _ in range(n):
        ctypes.windll.user32.keybd_event(k,0,0,0)
        ctypes.windll.user32.keybd_event(k,0,2,0)
        time.sleep(0.05)

def volume_up(): _press(VK_VOLUME_UP, 5)
def volume_down(): _press(VK_VOLUME_DOWN, 5)
def mute_volume(): _press(VK_VOLUME_MUTE, 1)


# ==================================================
# BRIGHTNESS
# ==================================================

def _safe_wmi():
    try:
        pythoncom.CoInitialize()
        return wmi.WMI(namespace="wmi")
    except Exception:
        return None

def brightness_up():
    try:
        c = _safe_wmi()
        if not c: return
        v = c.WmiMonitorBrightness()[0].CurrentBrightness
        c.WmiMonitorBrightnessMethods()[0].WmiSetBrightness(0, min(100, v+10))
    except Exception:
        pass

def brightness_down():
    try:
        c = _safe_wmi()
        if not c: return
        v = c.WmiMonitorBrightness()[0].CurrentBrightness
        c.WmiMonitorBrightnessMethods()[0].WmiSetBrightness(0, max(0, v-10))
    except Exception:
        pass

def brightness_max():
    try:
        c = _safe_wmi()
        if not c: return
        c.WmiMonitorBrightnessMethods()[0].WmiSetBrightness(0, 100)
    except Exception:
        pass

def brightness_low():
    try:
        c = _safe_wmi()
        if not c: return
        c.WmiMonitorBrightnessMethods()[0].WmiSetBrightness(0, 20)
    except Exception:
        pass


def shutdown_system(): os.system("shutdown /s /t 5")
def restart_system(): os.system("shutdown /r /t 5")
