"""
Thread-sichere UI-Aufrufe für tkinter (Queue + after-Poll).
"""

import queue
from typing import Callable, Optional


class UiDispatch:
    def __init__(self, root, interval_ms: int = 50):
        self.root = root
        self.interval_ms = interval_ms
        self._q: queue.Queue = queue.Queue()
        self._job = None
        self._alive = True
        self._poll()

    def call(self, fn: Callable, *args, **kwargs):
        """Beliebiger Thread: Aktion in die UI-Queue legen."""
        if not self._alive:
            return
        self._q.put((fn, args, kwargs))

    def _poll(self):
        if not self._alive:
            return
        try:
            while True:
                fn, args, kwargs = self._q.get_nowait()
                try:
                    fn(*args, **kwargs)
                except Exception:
                    pass
        except queue.Empty:
            pass
        self._job = self.root.after(self.interval_ms, self._poll)

    def stop(self):
        self._alive = False
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
