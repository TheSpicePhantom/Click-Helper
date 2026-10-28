"""
Auto-Clicker – win32api/ctypes, threading ohne PyQt.
"""

import threading
import time

from .logger_service import get_logger

try:
    import win32api
    import win32con

    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    import ctypes


class AutoClickerThread:
    def __init__(self, interval: float, button: str, enabled: bool = True):
        self.interval = interval
        self.button = button
        self.enabled = enabled
        self.running = False
        self._thread = None
        self.logger = get_logger()
        self.click_method = self._win32_click if HAS_WIN32 else self._ctypes_click

    def _win32_click(self, button):
        mapping = {
            "left": (win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP),
            "right": (win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP),
            "middle": (win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP),
        }
        down, up = mapping.get(button, mapping["left"])
        win32api.mouse_event(down, 0, 0, 0, 0)
        win32api.mouse_event(up, 0, 0, 0, 0)

    def _ctypes_click(self, button):
        mapping = {
            "left": (0x0002, 0x0004),
            "right": (0x0008, 0x0010),
            "middle": (0x0020, 0x0040),
        }
        down, up = mapping.get(button, mapping["left"])
        ctypes.windll.user32.mouse_event(down, 0, 0, 0, 0)
        ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)

    def start(self):
        if self.isRunning():
            return
        self.running = True
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def isRunning(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def wait(self, timeout_ms: int = None):
        if self._thread is None:
            return
        timeout_s = None if timeout_ms is None else max(0.0, timeout_ms / 1000.0)
        self._thread.join(timeout=timeout_s)

    def run(self):
        click_count = 0
        start_time = time.time()
        next_click = start_time
        compensation = 0.001

        while self.running and self.enabled:
            try:
                now = time.time()
                if now < next_click:
                    time.sleep(max(0.0001, next_click - now))
                    continue

                self.click_method(self.button)
                click_count += 1
                comp = (
                    compensation * (50 / self.interval)
                    if self.interval < 50
                    else compensation
                )
                next_click = start_time + (click_count * self.interval / 1000.0) - comp
            except Exception as e:
                self.logger.error(f"Auto-Click Fehler: {e}")
                break

    def stop(self):
        self.running = False
