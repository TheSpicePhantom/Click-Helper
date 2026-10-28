"""
Adapter: View ↔ Model (Status, Halten, Konfigurieren, Datenordner).
"""

from pathlib import Path
from typing import Any, Dict, Set

import keyboard
from tkinter import messagebox

from model.auto_clicker import AutoClickerThread
from model.hotkey_manager import HotkeyManager, normalize_hotkey_name
from model.logger_service import get_logger
from model.process_manager import ProcessManager
from view.hotkey_tab import HotkeyTab


class HotkeyAdapter:
    def __init__(self, hotkey_tab: HotkeyTab, ui_dispatch=None):
        self.hotkey_tab = hotkey_tab
        self.ui = ui_dispatch
        self.logger = get_logger()

        data_dir = hotkey_tab.get_data_directory()
        if data_dir is None:
            raise ValueError("Datenverzeichnis muss vor Adapter-Erstellung gesetzt sein")

        self.hotkey_manager = HotkeyManager(data_dir)
        self.process_manager = ProcessManager()
        self.auto_clicker_threads: Dict[str, AutoClickerThread] = {}
        self._hold_hotkeys: Dict[str, Dict[str, Any]] = {}
        self._hold_hook = None
        self._monitor_job = None

        self.hotkey_tab.set_add_hotkey_callback(self.add_hotkey)
        self.hotkey_tab.set_remove_hotkey_callback(self.remove_hotkey)
        self.hotkey_tab.set_configure_hotkey_callback(self.configure_hotkey)
        self.register_all_hotkeys()
        self._maybe_start_monitor()

    def _maybe_start_monitor(self):
        if self._monitor_job is not None:
            return
        if not self.hotkey_manager.has_window_restrictions():
            return
        self._schedule_monitor()

    def _schedule_monitor(self):
        self.monitor_active_windows()
        self._monitor_job = self.hotkey_tab.after(1000, self._schedule_monitor)

    def _stop_monitor(self):
        if self._monitor_job is not None:
            try:
                self.hotkey_tab.after_cancel(self._monitor_job)
            except Exception:
                pass
            self._monitor_job = None

    def add_hotkey(self):
        raw = self.hotkey_tab.get_hotkey_input_text()
        hotkey = normalize_hotkey_name(raw)
        function = self.hotkey_tab.get_function_type()

        if not hotkey:
            messagebox.showwarning("Fehler", "Bitte Hotkey aufnehmen.")
            return
        if self.hotkey_manager.hotkey_exists(hotkey):
            messagebox.showwarning(
                "Doppelbelegung",
                f"„{hotkey}“ ist bereits vergeben.\nBitte anderen Hotkey wählen.",
            )
            return

        restrictions = self.hotkey_tab.get_window_restrictions()

        if function == "Text eingeben":
            text = self.hotkey_tab.get_text_input()
            if not text:
                messagebox.showwarning("Fehler", "Bitte Text eingeben.")
                return
            data = {"type": "text", "data": text, "conditions": restrictions}
        else:
            cps = self.hotkey_tab.get_cps_value()
            button = self.hotkey_tab.get_button_value() or "left"
            if cps > 20 and not messagebox.askyesno(
                "Warnung", f"{cps} CPS ist sehr schnell. Fortfahren?"
            ):
                return
            data = {
                "type": "clicker",
                "interval": 1000.0 / cps if cps > 0 else 1000.0,
                "button": button,
                "trigger": self.hotkey_tab.get_trigger_mode(),
                "conditions": restrictions,
            }

        if self.hotkey_manager.add_hotkey(hotkey, data):
            stored = self.hotkey_manager.get_hotkey(hotkey)
            self.register_hotkey(hotkey, stored or data)
            self.update_view()
            self.hotkey_tab.clear_inputs()
            if restrictions.get("window_restriction"):
                self._maybe_start_monitor()
        else:
            messagebox.showwarning("Fehler", "Hotkey konnte nicht hinzugefügt werden.")

    def remove_hotkey(self, hotkey):
        hotkey = normalize_hotkey_name(hotkey)
        if hotkey in self.auto_clicker_threads:
            self.stop_clicker_for_hotkey(hotkey)
        self._unregister_hotkey(hotkey)
        if self.hotkey_manager.remove_hotkey(hotkey):
            self.update_view()
        else:
            messagebox.showwarning("Fehler", "Hotkey konnte nicht entfernt werden.")

    def configure_hotkey(self, hotkey: str, *, cps: float = None, trigger: str = None):
        """CPS und/oder Trigger ändern; Taste bleibt."""
        hotkey = normalize_hotkey_name(hotkey)
        data = self.hotkey_manager.get_hotkey(hotkey)
        if not data:
            messagebox.showwarning("Fehler", "Hotkey nicht gefunden.")
            return False
        if data.get("type") != "clicker":
            messagebox.showinfo(
                "Konfigurieren",
                "CPS und Umschalten/Halten gelten nur für Auto-Clicker.",
            )
            return False

        was_running = hotkey in self.auto_clicker_threads
        if was_running:
            self.stop_clicker_for_hotkey(hotkey)

        self._unregister_hotkey(hotkey)

        interval = None
        if cps is not None:
            interval = 1000.0 / float(cps) if cps > 0 else 1000.0

        if not self.hotkey_manager.update_clicker(
            hotkey, interval=interval, trigger=trigger
        ):
            messagebox.showwarning("Fehler", "Konfiguration ungültig.")
            stored = self.hotkey_manager.get_hotkey(hotkey)
            if stored:
                self.register_hotkey(hotkey, stored)
            self.update_view()
            return False

        stored = self.hotkey_manager.get_hotkey(hotkey)
        self.register_hotkey(hotkey, stored)
        self.update_view()
        return True

    def change_data_directory(self, new_dir: Path) -> Path:
        """Neuen Datenordner setzen und Hotkeys dorthin speichern."""
        new_dir = Path(new_dir)
        path = self.hotkey_manager.set_data_dir(new_dir, migrate=True)
        self.hotkey_tab.set_data_directory(path)
        return path

    def _unregister_hotkey(self, hotkey):
        hotkey = normalize_hotkey_name(hotkey)
        if hotkey in self._hold_hotkeys:
            del self._hold_hotkeys[hotkey]
            self._sync_hold_hook()
            return
        try:
            keyboard.remove_hotkey(hotkey)
        except (ValueError, KeyError):
            pass
        except Exception as e:
            self.logger.warning(f"Unregister fehlgeschlagen: {hotkey} - {e}")

    def _unregister_all(self):
        for hotkey in list(self.hotkey_manager.get_all_hotkeys()):
            self._unregister_hotkey(hotkey)
        self._hold_hotkeys.clear()
        self._sync_hold_hook()

    def _sync_hold_hook(self):
        if self._hold_hotkeys and self._hold_hook is None:
            self._hold_hook = keyboard.hook(self._on_hold_event, suppress=False)
        elif not self._hold_hotkeys and self._hold_hook is not None:
            try:
                keyboard.unhook(self._hold_hook)
            except Exception:
                pass
            self._hold_hook = None

    def _on_hold_event(self, event):
        for hotkey, data in list(self._hold_hotkeys.items()):
            try:
                pressed = keyboard.is_pressed(hotkey)
            except Exception:
                continue
            running = hotkey in self.auto_clicker_threads
            if pressed and not running:
                self.start_clicker_for_hotkey(hotkey, data)
            elif not pressed and running:
                self.stop_clicker_for_hotkey(hotkey)

    def register_hotkey(self, hotkey, data):
        hotkey = normalize_hotkey_name(hotkey)
        try:
            if data["type"] == "text":
                payload = data["data"]
                keyboard.add_hotkey(hotkey, lambda t=payload: self.type_text(t))
            elif data.get("trigger", "toggle") == "hold":
                self._hold_hotkeys[hotkey] = data
                self._sync_hold_hook()
            else:
                keyboard.add_hotkey(
                    hotkey, lambda h=hotkey, d=data: self.handle_clicker_action(h, d)
                )
        except Exception as e:
            messagebox.showwarning("Fehler", f"Registrierung fehlgeschlagen: {e}")

    def register_all_hotkeys(self):
        for hotkey, data in self.hotkey_manager.get_all_hotkeys().items():
            self.register_hotkey(hotkey, data)
        self.update_view()

    def type_text(self, text):
        try:
            import pyautogui

            pyautogui.write(text)
        except Exception as e:
            self.logger.error(f"Text-Eingabe fehlgeschlagen: {e}")

    def handle_clicker_action(self, hotkey, data):
        hotkey = normalize_hotkey_name(hotkey)
        if hotkey in self.auto_clicker_threads:
            self.stop_clicker_for_hotkey(hotkey)
        else:
            self.start_clicker_for_hotkey(hotkey, data)

    def start_clicker_for_hotkey(self, hotkey, data):
        hotkey = normalize_hotkey_name(hotkey)
        if hotkey in self.auto_clicker_threads:
            self.stop_clicker_for_hotkey(hotkey)
        thread = AutoClickerThread(data["interval"], data["button"], True)
        thread.start()
        self.auto_clicker_threads[hotkey] = thread
        self.update_view()

    def stop_clicker_for_hotkey(self, hotkey):
        hotkey = normalize_hotkey_name(hotkey)
        thread = self.auto_clicker_threads.pop(hotkey, None)
        if not thread:
            return
        thread.stop()
        thread.wait(2000)
        self.update_view()

    def update_view(self):
        running: Set[str] = set(self.auto_clicker_threads.keys())
        hotkeys = self.hotkey_manager.get_all_hotkeys()

        def do_update():
            self.hotkey_tab.update_table(hotkeys, running)

        if self.ui is not None:
            self.ui.call(do_update)
            return
        try:
            self.hotkey_tab.after(0, do_update)
        except Exception:
            do_update()

    def stop_all_clickers(self):
        for hotkey in list(self.auto_clicker_threads):
            self.stop_clicker_for_hotkey(hotkey)
        self._stop_monitor()
        if self._hold_hook is not None:
            try:
                keyboard.unhook(self._hold_hook)
            except Exception:
                pass
            self._hold_hook = None
        self._hold_hotkeys.clear()

    def monitor_active_windows(self):
        try:
            current = self.process_manager.get_current_active_window()
            for hotkey in list(self.auto_clicker_threads):
                if not self.hotkey_manager.check_hotkey_conditions(hotkey, current):
                    self.stop_clicker_for_hotkey(hotkey)
        except Exception as e:
            self.logger.error(f"Fenster-Monitor: {e}")

    def get_active_windows(self):
        return self.process_manager.get_active_windows()

    def get_process_list(self):
        return self.process_manager.get_process_list()

    def get_active_threads_info(self):
        return {
            h: {"running": t.isRunning(), "interval": t.interval, "button": t.button}
            for h, t in self.auto_clicker_threads.items()
        }

    def update_hotkey_conditions(self, hotkey: str, conditions: Dict[str, Any]):
        ok = self.hotkey_manager.update_hotkey_conditions(hotkey, conditions)
        if ok and conditions.get("window_restriction"):
            self._maybe_start_monitor()
        return ok
