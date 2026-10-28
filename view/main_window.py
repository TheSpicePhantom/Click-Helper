"""
Hauptfenster – Zahnrad für Speicherort, GitHub-Link, X/Minimieren → Tray.
"""

import os
import subprocess
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from model.app_settings import GITHUB_REPO_URL, default_data_dir
from model.resources import resource_path
from .hotkey_tab import HotkeyTab


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.hide_callback = None
        self.data_dir = None
        self.settings = None
        self.on_data_dir_changed = None
        self.root.title("Click Helper")
        self.root.geometry("760x620")
        self.root.minsize(620, 480)

        icon = resource_path("icon.png")
        if icon.exists():
            try:
                self.root.iconphoto(True, tk.PhotoImage(file=str(icon)))
            except Exception:
                pass

        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(frame)
        header.pack(fill=tk.X, pady=(0, 8))

        titles = ttk.Frame(header)
        titles.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(titles, text="Click Helper", font=("Segoe UI", 16, "bold")).pack(
            anchor=tk.W
        )
        ttk.Label(
            titles,
            text="Lightweight auto-clicker & text hotkeys for Windows",
            foreground="gray",
        ).pack(anchor=tk.W)

        # Equal-size icon buttons (GitHub left of gear)
        self._header_imgs = []
        gh_box, self.github_btn = self._make_header_icon_button(
            header,
            icon_name="github.png",
            fallback_text="GH",
            command=self._open_github,
        )
        gear_box, self.gear_btn = self._make_header_icon_button(
            header,
            icon_name="gear.png",
            fallback_text="⚙",
            command=self._show_storage_settings,
        )
        gear_box.pack(side=tk.RIGHT)
        gh_box.pack(side=tk.RIGHT, padx=(0, 6))
        self._set_tooltip(self.gear_btn, "Where your hotkeys are saved")
        self._set_tooltip(
            self.github_btn, "Open source code, README & license on GitHub"
        )

        self.hotkey_tab = HotkeyTab(frame)
        self.hotkey_tab.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="Tip: Close or minimize to keep running in the tray · Ctrl+Q or tray → Exit to quit",
            foreground="gray",
        ).pack(anchor=tk.W, pady=(8, 0))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Unmap>", self._on_unmap)

    def set_settings(self, settings):
        self.settings = settings

    def set_data_dir_changed_callback(self, callback):
        self.on_data_dir_changed = callback

    def _make_header_icon_button(self, parent, *, icon_name: str, fallback_text: str, command):
        """Square header control – same pixel size for GitHub and gear."""
        size = 28
        box = ttk.Frame(parent, width=size, height=size)
        box.pack_propagate(False)

        img = None
        path = resource_path(icon_name)
        if path.exists():
            try:
                img = tk.PhotoImage(file=str(path))
                self._header_imgs.append(img)
            except Exception:
                img = None

        if img is not None:
            btn = ttk.Button(box, image=img, command=command)
        else:
            btn = ttk.Button(box, text=fallback_text, command=command)
        btn.pack(fill=tk.BOTH, expand=True)
        return box, btn

    def _open_github(self):
        try:
            webbrowser.open(GITHUB_REPO_URL)
        except Exception as e:
            messagebox.showerror(
                "GitHub",
                f"Could not open link:\n{GITHUB_REPO_URL}\n\n{e}",
            )

    def _set_tooltip(self, widget, text: str):
        tip = {"win": None}

        def show(_event):
            if tip["win"] is not None:
                return
            x = widget.winfo_rootx()
            y = widget.winfo_rooty() + widget.winfo_height() + 4
            win = tk.Toplevel(self.root)
            win.wm_overrideredirect(True)
            win.wm_geometry(f"+{x}+{y}")
            ttk.Label(win, text=text, padding=(6, 2), relief="solid").pack()
            tip["win"] = win

        def hide(_event):
            if tip["win"] is not None:
                tip["win"].destroy()
                tip["win"] = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def _show_storage_settings(self):
        path = self.data_dir or default_data_dir()

        dialog = tk.Toplevel(self.root)
        dialog.title("Save location")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="Your hotkeys are stored in this folder",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            frame,
            text="You can move this folder anytime (e.g. onto a USB drive).",
            foreground="gray",
        ).pack(anchor=tk.W, pady=(0, 8))

        path_var = tk.StringVar(value=str(path))
        entry = ttk.Entry(frame, textvariable=path_var, width=56, state="readonly")
        entry.pack(fill=tk.X, pady=(0, 10))

        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X)

        def choose_folder():
            chosen = filedialog.askdirectory(
                parent=dialog,
                title="Choose folder for your hotkeys",
                initialdir=str(path),
            )
            if not chosen:
                return
            new_path = Path(chosen)
            try:
                if self.on_data_dir_changed:
                    applied = self.on_data_dir_changed(new_path)
                    path_var.set(str(applied))
                else:
                    path_var.set(str(new_path))
                messagebox.showinfo(
                    "Save location",
                    f"Hotkeys will now be saved here:\n{path_var.get()}",
                    parent=dialog,
                )
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dialog)

        def open_folder():
            self._open_path(Path(path_var.get()))

        def reset_default():
            default = default_data_dir()
            if not messagebox.askyesno(
                "Reset",
                f"Use the default folder again?\n\n{default}",
                parent=dialog,
            ):
                return
            try:
                if self.on_data_dir_changed:
                    applied = self.on_data_dir_changed(default, reset_settings=True)
                    path_var.set(str(applied))
                else:
                    path_var.set(str(default))
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dialog)

        ttk.Button(btns, text="Change folder…", command=choose_folder).pack(side=tk.LEFT)
        ttk.Button(btns, text="Open folder", command=open_folder).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(btns, text="Use default", command=reset_default).pack(side=tk.LEFT)
        ttk.Button(btns, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)

        dialog.wait_window()

    def _open_path(self, path: Path):
        try:
            path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(path))
        except Exception:
            try:
                subprocess.Popen(["explorer", str(path)])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder:\n{e}")

    def set_hide_callback(self, callback):
        self.hide_callback = callback

    def set_close_callback(self, callback):
        self.set_hide_callback(callback)

    def _on_close(self):
        if self.hide_callback:
            self.hide_callback()
        else:
            self.root.withdraw()

    def _on_unmap(self, event):
        if event.widget is not self.root:
            return
        try:
            if self.root.state() == "iconic":
                if self.hide_callback:
                    self.hide_callback()
                else:
                    self.root.withdraw()
        except Exception:
            pass

    def get_hotkey_tab(self):
        return self.hotkey_tab

    def update_storage_info(self, data_dir):
        self.data_dir = Path(data_dir)

    def show(self):
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except Exception:
            pass

    def hide(self):
        self.root.withdraw()
