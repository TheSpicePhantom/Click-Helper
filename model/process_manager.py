"""
Fenster-/Prozess-Abfragen – lazy, ohne Scan beim Init.
"""

from typing import Dict, List, Optional

import psutil
import win32gui
import win32process

from .logger_service import get_logger


class ProcessManager:
    """Aktive Fenster und Prozesse für bedingte Hotkeys."""

    def __init__(self):
        self.logger = get_logger()
        self.active_windows: Dict[int, Dict] = {}

    def refresh_windows(self):
        self.active_windows.clear()

        def callback(hwnd, windows):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            try:
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return True
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if not pid:
                    return True
                try:
                    process = psutil.Process(pid)
                    windows[hwnd] = {
                        "title": title,
                        "pid": pid,
                        "process_name": process.name(),
                        "hwnd": hwnd,
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            except Exception:
                pass
            return True

        win32gui.EnumWindows(callback, self.active_windows)

    def get_active_windows(self) -> Dict[int, Dict]:
        if not self.active_windows:
            self.refresh_windows()
        return self.active_windows.copy()

    def get_current_active_window(self) -> Optional[Dict]:
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            name = ""
            try:
                name = psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            return {"title": title, "pid": pid, "process_name": name, "hwnd": hwnd}
        except Exception as e:
            self.logger.debug(f"Aktives Fenster nicht lesbar: {e}")
            return None

    def get_process_list(self) -> List[Dict]:
        processes = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                processes.append(
                    {"pid": proc.info["pid"], "name": proc.info["name"]}
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes
