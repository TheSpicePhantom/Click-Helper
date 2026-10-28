"""
Hotkey-Persistenz und Bedingungsprüfung.
"""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import keyboard

from .logger_service import get_logger

_DEFAULT_CONDITIONS = {
    "window_restriction": False,
    "allowed_windows": [],
    "allowed_processes": [],
}

_MOD_ALIASES = {
    "control": "ctrl",
    "strg": "ctrl",
    "win": "windows",
}


def normalize_hotkey_name(hotkey: str) -> str:
    """Einheitlicher Hotkey-Schlüssel (keine Doppelbelegung durch Schreibweise)."""
    if not isinstance(hotkey, str):
        return ""
    parts = [
        p.strip().lower()
        for p in hotkey.replace("-", "+").replace(" ", "").split("+")
        if p.strip()
    ]
    if not parts:
        return ""
    mapped = [_MOD_ALIASES.get(p, p) for p in parts]
    key = mapped[-1]
    mods = sorted(
        {m for m in mapped[:-1] if m in ("ctrl", "alt", "shift", "windows")}
    )
    return "+".join(mods + [key])


class HotkeyManager:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.hotkeys: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.load_hotkeys()

    def _normalize(self, hotkey: str, hotkey_data: Any) -> Optional[Dict[str, Any]]:
        key = normalize_hotkey_name(hotkey)
        if not key:
            return None
        if not isinstance(hotkey_data, dict):
            return None

        entry_type = hotkey_data.get("type")
        if entry_type == "text":
            text = hotkey_data.get("data")
            if not isinstance(text, str) or not text:
                return None
            normalized = {"type": "text", "data": text}
        elif entry_type == "clicker":
            interval = hotkey_data.get("interval")
            button = hotkey_data.get("button", "left")
            try:
                interval = float(interval)
            except (TypeError, ValueError):
                return None
            if interval <= 0:
                return None
            if button not in ("left", "right", "middle", "x1", "x2"):
                button = "left"
            trigger = hotkey_data.get("trigger", "toggle")
            if trigger not in ("toggle", "hold"):
                trigger = "toggle"
            normalized = {
                "type": "clicker",
                "interval": interval,
                "button": button,
                "trigger": trigger,
            }
        else:
            return None

        conditions = hotkey_data.get("conditions")
        if not isinstance(conditions, dict):
            conditions = dict(_DEFAULT_CONDITIONS)
        else:
            conditions = {
                "window_restriction": bool(conditions.get("window_restriction", False)),
                "allowed_windows": list(conditions.get("allowed_windows") or []),
                "allowed_processes": list(conditions.get("allowed_processes") or []),
            }
        normalized["conditions"] = conditions
        return normalized

    def add_hotkey(self, hotkey: str, hotkey_data: Dict[str, Any]) -> bool:
        key = normalize_hotkey_name(hotkey)
        if not key or key in self.hotkeys:
            return False
        normalized = self._normalize(key, hotkey_data)
        if normalized is None:
            return False
        self.hotkeys[key] = normalized
        self.save_hotkeys()
        return True

    def update_clicker(
        self, hotkey: str, *, interval: float = None, trigger: str = None, button: str = None
    ) -> bool:
        """Ändert CPS/Trigger/Button; Hotkey-Taste bleibt."""
        key = normalize_hotkey_name(hotkey)
        data = self.hotkeys.get(key)
        if not data or data.get("type") != "clicker":
            return False
        if interval is not None:
            interval = float(interval)
            if interval <= 0:
                return False
            data["interval"] = interval
        if trigger is not None:
            if trigger not in ("toggle", "hold"):
                return False
            data["trigger"] = trigger
        if button is not None:
            if button not in ("left", "right", "middle", "x1", "x2"):
                return False
            data["button"] = button
        self.save_hotkeys()
        return True

    def set_data_dir(self, new_dir: Path, migrate: bool = True) -> Path:
        """Wechselt den Datenordner und speichert die aktuelle Konfiguration dort."""
        new_dir = Path(new_dir)
        new_dir.mkdir(parents=True, exist_ok=True)
        old_file = self.data_dir / "hotkeys.json"
        new_file = new_dir / "hotkeys.json"
        if migrate and old_file.exists() and old_file.resolve() != new_file.resolve():
            if not new_file.exists():
                try:
                    shutil.copy2(old_file, new_file)
                except Exception as e:
                    self.logger.warning(f"Migration fehlgeschlagen: {e}")
        self.data_dir = new_dir
        self.save_hotkeys()
        return self.data_dir

    def replace_all(self, hotkeys: Dict[str, Any]) -> Tuple[int, int]:
        if not isinstance(hotkeys, dict):
            return 0, 0

        accepted: Dict[str, Dict[str, Any]] = {}
        skipped = 0
        for key, data in hotkeys.items():
            norm_key = normalize_hotkey_name(key)
            normalized = self._normalize(norm_key, data)
            if normalized is None or not norm_key:
                skipped += 1
                continue
            if norm_key in accepted:
                skipped += 1
                continue
            accepted[norm_key] = normalized

        self.hotkeys = accepted
        self.save_hotkeys()
        return len(accepted), skipped

    def remove_hotkey(self, hotkey: str) -> bool:
        key = normalize_hotkey_name(hotkey)
        if key not in self.hotkeys:
            return False
        try:
            keyboard.remove_hotkey(key)
        except (ValueError, KeyError):
            pass
        except Exception as e:
            self.logger.warning(f"Hotkey-Unregister fehlgeschlagen: {key} - {e}")
        del self.hotkeys[key]
        self.save_hotkeys()
        return True

    def get_hotkey(self, hotkey: str) -> Optional[Dict[str, Any]]:
        return self.hotkeys.get(normalize_hotkey_name(hotkey))

    def get_all_hotkeys(self) -> Dict[str, Dict[str, Any]]:
        return self.hotkeys.copy()

    def hotkey_exists(self, hotkey: str) -> bool:
        return normalize_hotkey_name(hotkey) in self.hotkeys

    def update_hotkey_conditions(self, hotkey: str, conditions: Dict[str, Any]) -> bool:
        key = normalize_hotkey_name(hotkey)
        if key not in self.hotkeys:
            return False
        self.hotkeys[key]["conditions"] = conditions
        self.save_hotkeys()
        return True

    def has_window_restrictions(self) -> bool:
        for data in self.hotkeys.values():
            if data.get("conditions", {}).get("window_restriction"):
                return True
        return False

    def check_hotkey_conditions(
        self, hotkey: str, current_window: Optional[Dict] = None
    ) -> bool:
        data = self.hotkeys.get(normalize_hotkey_name(hotkey))
        if not data:
            return False
        conditions = data.get("conditions", {})
        if not conditions.get("window_restriction", False):
            return True
        if not current_window:
            return False

        allowed_windows = conditions.get("allowed_windows", [])
        if allowed_windows:
            title = current_window.get("title", "").lower()
            if not any(a.lower() in title for a in allowed_windows):
                return False

        allowed_processes = conditions.get("allowed_processes", [])
        if allowed_processes:
            name = current_window.get("process_name", "").lower()
            if not any(a.lower() in name for a in allowed_processes):
                return False
        return True

    def load_hotkeys(self):
        path = self.data_dir / "hotkeys.json"
        if not path.exists():
            self.hotkeys = {}
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            accepted = {}
            if isinstance(raw, dict):
                for key, data in raw.items():
                    norm_key = normalize_hotkey_name(key)
                    normalized = self._normalize(norm_key, data)
                    if normalized is not None and norm_key and norm_key not in accepted:
                        accepted[norm_key] = normalized
            self.hotkeys = accepted
        except Exception as e:
            self.logger.error(f"Hotkeys laden fehlgeschlagen: {e}")
            self.hotkeys = {}

    def save_hotkeys(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self.data_dir / "hotkeys.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.hotkeys, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Hotkeys speichern fehlgeschlagen: {e}")
            raise
