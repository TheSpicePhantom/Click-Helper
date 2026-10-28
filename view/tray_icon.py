"""
System-Tray über pywin32 – WndProc setzt nur Flags, kein tkinter darin.
"""

import win32api
import win32con
import win32gui

from model.resources import resource_path


class TrayIcon:
    """Tray-Icon mit Menü Anzeigen / Beenden."""

    WM_TRAY = win32con.WM_USER + 20

    def __init__(self, root, on_show, on_quit, icon_path: str = None):
        self.root = root
        self.on_show = on_show
        self.on_quit = on_quit
        self._hwnd = None
        self._hicon = None
        self._class_atom = None
        self._class_name = None
        self._visible = False
        self._pump_job = None
        self._pending_show = False
        self._pending_quit = False
        self._pending_menu = False
        self._icon_path = icon_path or self._default_icon_path()
        self._create()

    def _default_icon_path(self) -> str:
        ico = resource_path("icon.ico")
        if ico.exists():
            return str(ico)
        return str(resource_path("icon.png"))

    def _load_icon(self):
        path = self._icon_path
        if path and path.lower().endswith(".ico"):
            from pathlib import Path

            if Path(path).exists():
                try:
                    return win32gui.LoadImage(
                        0,
                        path,
                        win32con.IMAGE_ICON,
                        0,
                        0,
                        win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
                    )
                except Exception:
                    pass
        return win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

    def _create(self):
        message_map = {
            self.WM_TRAY: self._on_tray,
            win32con.WM_DESTROY: self._on_destroy,
            win32con.WM_COMMAND: self._on_command,
        }

        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        self._class_name = f"ClickHelperTray{id(self)}"
        wc.lpszClassName = self._class_name
        wc.lpfnWndProc = message_map
        self._class_atom = win32gui.RegisterClass(wc)

        self._hwnd = win32gui.CreateWindow(
            self._class_name,
            "ClickHelperTrayWnd",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            wc.hInstance,
            None,
        )
        self._hicon = self._load_icon()

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self._hwnd, 0, flags, self.WM_TRAY, self._hicon, "Click Helper")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        self._visible = True
        self._schedule_pump()

    def _schedule_pump(self):
        if self._pump_job is not None:
            return

        def pump():
            self._pump_job = None
            if not self._visible:
                return
            try:
                win32gui.PumpWaitingMessages()
            except Exception:
                pass
            # tkinter erst NACH dem Message-Pump, nie aus dem WndProc
            self._flush_pending()
            if self._visible:
                self._pump_job = self.root.after(100, pump)

        self._pump_job = self.root.after(100, pump)

    def _flush_pending(self):
        if self._pending_menu:
            self._pending_menu = False
            try:
                self._show_menu()
            except Exception:
                pass
            # Menü pumpt selbst Nachrichten; danach erneut Flags lesen
            try:
                win32gui.PumpWaitingMessages()
            except Exception:
                pass

        do_show = self._pending_show
        do_quit = self._pending_quit
        self._pending_show = False
        self._pending_quit = False

        if do_quit:
            try:
                self.on_quit()
            except Exception:
                pass
            return

        if do_show:
            try:
                self.on_show()
            except Exception:
                pass

    def _on_tray(self, hwnd, msg, wparam, lparam):
        # Nur Flags – kein tkinter / kein root.after hier
        if lparam in (win32con.WM_LBUTTONUP, win32con.WM_LBUTTONDBLCLK):
            self._pending_show = True
        elif lparam == win32con.WM_RBUTTONUP:
            self._pending_menu = True
        return 1

    def _on_command(self, hwnd, msg, wparam, lparam):
        cmd = win32api.LOWORD(wparam)
        if cmd == 1001:
            self._pending_show = True
        elif cmd == 1002:
            self._pending_quit = True
        return 0

    def _on_destroy(self, hwnd, msg, wparam, lparam):
        return 0

    def _show_menu(self):
        if not self._hwnd:
            return
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1001, "Anzeigen")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1002, "Beenden")
        pos = win32gui.GetCursorPos()
        try:
            win32gui.SetForegroundWindow(self._hwnd)
        except Exception:
            pass
        win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON,
            pos[0],
            pos[1],
            0,
            self._hwnd,
            None,
        )
        win32gui.PostMessage(self._hwnd, win32con.WM_NULL, 0, 0)
        win32gui.DestroyMenu(menu)

    def destroy(self):
        self._visible = False
        if self._pump_job is not None:
            try:
                self.root.after_cancel(self._pump_job)
            except Exception:
                pass
            self._pump_job = None
        if self._hwnd:
            try:
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self._hwnd, 0))
            except Exception:
                pass
            try:
                win32gui.DestroyWindow(self._hwnd)
            except Exception:
                pass
            self._hwnd = None
        if self._class_atom and self._class_name:
            try:
                win32gui.UnregisterClass(
                    self._class_name, win32api.GetModuleHandle(None)
                )
            except Exception:
                pass
            self._class_atom = None
            self._class_name = None
