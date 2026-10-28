#!/usr/bin/env python3
"""
Click Helper – einziger Einstieg (MVA + tkinter).
"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import keyboard

from adapter.hotkey_adapter import HotkeyAdapter
from model.app_settings import AppSettings, default_data_dir
from model.logger_service import get_logger
from view.main_window import MainWindow
from view.tray_icon import TrayIcon
from view.ui_dispatch import UiDispatch


class ClickHelperApp:
    def __init__(self):
        self.logger = get_logger()
        self.root = tk.Tk()
        self.root.withdraw()
        self.tray = None
        self._closing = False

        self.settings = AppSettings()
        self.ui = UiDispatch(self.root)

        self.main_window = MainWindow(self.root)
        self.main_window.set_hide_callback(self.hide_to_tray)
        self.main_window.set_settings(self.settings)
        self.main_window.set_data_dir_changed_callback(self.change_data_dir)

        data_dir = self.settings.get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        tab = self.main_window.get_hotkey_tab()
        tab.set_data_directory(data_dir)
        self.main_window.update_storage_info(data_dir)

        self.hotkey_adapter = HotkeyAdapter(tab, ui_dispatch=self.ui)
        tab.set_adapter(self.hotkey_adapter)

        keyboard.add_hotkey("ctrl+q", lambda: self.ui.call(self.close_app))

        try:
            self.tray = TrayIcon(
                self.root,
                on_show=self.show_from_tray,
                on_quit=self.close_app,
            )
        except Exception as e:
            self.logger.warning(f"Tray nicht verfügbar: {e}")
            self.tray = None
            self.main_window.set_hide_callback(self.close_app)

    def change_data_dir(self, new_dir: Path, reset_settings: bool = False) -> Path:
        target = default_data_dir() if reset_settings else Path(new_dir)
        applied = self.hotkey_adapter.change_data_directory(target)
        if reset_settings:
            self.settings.reset_data_dir()
        else:
            self.settings.set_data_dir(applied)
        self.main_window.update_storage_info(applied)
        return applied

    def hide_to_tray(self):
        if self._closing:
            return
        self.main_window.hide()

    def show_from_tray(self):
        if self._closing:
            return
        self.main_window.show()

    def close_app(self):
        if self._closing:
            return
        self._closing = True

        try:
            self.hotkey_adapter.stop_all_clickers()
        except Exception:
            pass
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        if self.tray is not None:
            try:
                self.tray.destroy()
            except Exception:
                pass
            self.tray = None
        try:
            self.ui.stop()
        except Exception:
            pass
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.main_window.show()
        self.root.mainloop()
        return 0


def main():
    try:
        app = ClickHelperApp()
        sys.exit(app.run())
    except Exception as e:
        try:
            get_logger().critical(f"Startfehler: {e}")
        except Exception:
            pass
        try:
            messagebox.showerror("Fehler", f"Start fehlgeschlagen:\n{e}")
        except Exception:
            print(f"Fehler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
