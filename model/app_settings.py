"""
Portable App-Einstellungen neben der EXE / dem Skript.
"""

import json
import sys
from pathlib import Path
from typing import Optional


SETTINGS_FILE = "click_helper_settings.json"
GITHUB_REPO_URL = "https://github.com/TheSpicePhantom/Click-Helper"


def get_app_base_dir() -> Path:
    """Ordner der EXE (frozen) bzw. Projektwurzel (Entwicklung)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def default_data_dir() -> Path:
    return Path.home() / "Documents" / "Click-Helper"


class AppSettings:
    def __init__(self):
        self.base_dir = get_app_base_dir()
        self.settings_path = self.base_dir / SETTINGS_FILE
        self._data_dir: Optional[Path] = None
        self.load()

    def load(self):
        self._data_dir = None
        if not self.settings_path.exists():
            return
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            path = raw.get("data_dir")
            if isinstance(path, str) and path.strip():
                self._data_dir = Path(path)
        except Exception:
            self._data_dir = None

    def save(self):
        payload = {}
        if self._data_dir is not None:
            payload["data_dir"] = str(self._data_dir)
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_data_dir(self) -> Path:
        if self._data_dir is not None:
            return self._data_dir
        return default_data_dir()

    def set_data_dir(self, path: Path):
        self._data_dir = Path(path)
        self.save()

    def reset_data_dir(self):
        self._data_dir = None
        if self.settings_path.exists():
            try:
                self.settings_path.unlink()
            except Exception:
                self.save()
        else:
            self.save()
