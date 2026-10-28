"""
Hotkey tab – clear form flow for end users.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import keyboard

PLACEHOLDER = "Click here, then press your keys…"
RECORDING_HINT = "Listening… (ESC cancels)"
FUNC_TEXT = "Type text"
FUNC_CLICKER = "Auto-clicker"

MODE_TOGGLE = "Toggle — press once to start, again to stop"
MODE_HOLD = "Hold — clicks only while the key is held"
MODE_TOGGLE_SHORT = "Toggle"
MODE_HOLD_SHORT = "Hold"

BUTTON_OPTIONS = [
    ("Left", "left"),
    ("Right", "right"),
    ("Middle", "middle"),
]
BUTTON_LABELS = {code: label for label, code in BUTTON_OPTIONS}
BUTTON_CODES = {label: code for label, code in BUTTON_OPTIONS}

LABEL_W = 12


class HotkeyTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.data_dir = None
        self.adapter = None
        self.recording_hotkey = False
        self.current_hotkey = []
        self.remove_hotkey_callback = None
        self.configure_hotkey_callback = None
        self._press_hook = None
        self._release_hook = None
        self._build()

    def set_adapter(self, adapter):
        self.adapter = adapter

    def set_data_directory(self, data_dir):
        self.data_dir = data_dir

    def get_data_directory(self):
        return self.data_dir

    def _labeled_row(self, parent, label_text: str) -> ttk.Frame:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=3)
        ttk.Label(row, text=label_text, width=LABEL_W, anchor=tk.W).pack(side=tk.LEFT)
        return row

    def _build(self):
        form = ttk.LabelFrame(self, text="Create a hotkey", padding=10)
        form.pack(fill=tk.X, padx=4, pady=(0, 6))

        ttk.Label(
            form,
            text="1. Record a key  ·  2. Choose what it does  ·  3. Add it",
            foreground="gray",
        ).pack(anchor=tk.W, pady=(0, 6))

        row = self._labeled_row(form, "Hotkey")
        self.hotkey_input = ttk.Entry(row)
        self.hotkey_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._set_placeholder()
        self.hotkey_input.bind("<Button-1>", self._on_hotkey_click)

        row = self._labeled_row(form, "Action")
        self.function_combo = ttk.Combobox(
            row,
            values=[FUNC_CLICKER, FUNC_TEXT],
            state="readonly",
            width=22,
        )
        self.function_combo.set(FUNC_CLICKER)
        self.function_combo.pack(side=tk.LEFT)
        self.function_combo.bind("<<ComboboxSelected>>", self._on_function_changed)

        # Reserved slot so options always sit ABOVE the Add button
        self.options_host = ttk.Frame(form)
        self.options_host.pack(fill=tk.X, pady=(4, 0))

        self.text_frame = ttk.Frame(self.options_host)
        ttk.Label(self.text_frame, text="Text to type").pack(anchor=tk.W)
        self.text_input = tk.Text(self.text_frame, height=2, wrap=tk.WORD)
        self.text_input.pack(fill=tk.X, pady=(2, 0))

        self.clicker_frame = ttk.Frame(self.options_host)

        row = self._labeled_row(self.clicker_frame, "Speed")
        self.cps_var = tk.IntVar(value=5)
        ttk.Spinbox(
            row, from_=1, to=1000, textvariable=self.cps_var, width=6
        ).pack(side=tk.LEFT)
        ttk.Label(row, text="clicks per second", foreground="gray").pack(
            side=tk.LEFT, padx=(8, 0)
        )

        row = self._labeled_row(self.clicker_frame, "Mouse")
        self.button_combo = ttk.Combobox(
            row,
            values=[label for label, _ in BUTTON_OPTIONS],
            state="readonly",
            width=10,
        )
        self.button_combo.set("Left")
        self.button_combo.pack(side=tk.LEFT)

        row = self._labeled_row(self.clicker_frame, "Mode")
        self.hold_var = tk.BooleanVar(value=False)
        self.mode_combo = ttk.Combobox(
            row,
            values=[MODE_TOGGLE_SHORT, MODE_HOLD_SHORT],
            state="readonly",
            width=10,
        )
        self.mode_combo.set(MODE_TOGGLE_SHORT)
        self.mode_combo.pack(side=tk.LEFT)
        self.mode_combo.bind("<<ComboboxSelected>>", self._sync_hold_from_mode)
        self.mode_hint = ttk.Label(self.clicker_frame, text=MODE_TOGGLE, foreground="gray")
        self.mode_hint.pack(anchor=tk.W, pady=(2, 0))

        self.restrict_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form,
            text="Only when certain windows or apps are in the foreground",
            variable=self.restrict_var,
            command=self._toggle_restrict,
        ).pack(anchor=tk.W, pady=(10, 0))

        self.restrict_frame = ttk.Frame(form)
        lists = ttk.Frame(self.restrict_frame)
        lists.pack(fill=tk.X, pady=(4, 0))
        left = ttk.Frame(lists)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        right = ttk.Frame(lists)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="Window titles").pack(anchor=tk.W)
        self.allowed_windows_list = tk.Listbox(left, height=3)
        self.allowed_windows_list.pack(fill=tk.X, pady=(2, 2))
        win_btns = ttk.Frame(left)
        win_btns.pack(fill=tk.X)
        ttk.Button(win_btns, text="Add window…", command=self.add_allowed_window).pack(
            side=tk.LEFT
        )
        ttk.Button(win_btns, text="Remove", command=self.remove_allowed_window).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        ttk.Label(right, text="App / process names").pack(anchor=tk.W)
        self.allowed_processes_list = tk.Listbox(right, height=3)
        self.allowed_processes_list.pack(fill=tk.X, pady=(2, 2))
        proc_btns = ttk.Frame(right)
        proc_btns.pack(fill=tk.X)
        ttk.Button(
            proc_btns, text="Add process…", command=self.add_allowed_process
        ).pack(side=tk.LEFT)
        ttk.Button(proc_btns, text="Remove", command=self.remove_allowed_process).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        self.add_btn = ttk.Button(form, text="Add hotkey")
        self.add_btn.pack(pady=(12, 2))

        list_frame = ttk.LabelFrame(self, text="Your hotkeys", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 0))

        ttk.Label(
            list_frame,
            text="Right-click a row to edit or delete · Double-click to edit",
            foreground="gray",
        ).pack(anchor=tk.W, pady=(0, 6))

        table_wrap = ttk.Frame(list_frame)
        table_wrap.pack(fill=tk.BOTH, expand=True)

        cols = ("hotkey", "action", "where", "status")
        self.hotkey_table = ttk.Treeview(
            table_wrap, columns=cols, show="headings", height=8
        )
        self.hotkey_table.heading("hotkey", text="Hotkey")
        self.hotkey_table.heading("action", text="What it does")
        self.hotkey_table.heading("where", text="Where")
        self.hotkey_table.heading("status", text="Status")
        self.hotkey_table.column("hotkey", width=100, minwidth=80)
        self.hotkey_table.column("action", width=280, minwidth=160)
        self.hotkey_table.column("where", width=100, minwidth=80)
        self.hotkey_table.column("status", width=80, minwidth=70)
        self.hotkey_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(
            table_wrap, orient=tk.VERTICAL, command=self.hotkey_table.yview
        )
        self.hotkey_table.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(label="Edit…", command=self._configure_selected)
        self._context_menu.add_command(label="Delete", command=self._delete_selected)
        self.hotkey_table.bind("<Button-3>", self._on_right_click)
        self.hotkey_table.bind("<Double-1>", lambda e: self._configure_selected())

        self._on_function_changed()

    def _sync_hold_from_mode(self, *_):
        hold = self.mode_combo.get() == MODE_HOLD_SHORT
        self.hold_var.set(hold)
        self.mode_hint.configure(text=MODE_HOLD if hold else MODE_TOGGLE)

    def _on_right_click(self, event):
        row = self.hotkey_table.identify_row(event.y)
        if row:
            self.hotkey_table.selection_set(row)
            self.hotkey_table.focus(row)
            try:
                self._context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self._context_menu.grab_release()

    def _selected_hotkey(self):
        sel = self.hotkey_table.selection()
        if not sel:
            return None
        return self.hotkey_table.item(sel[0], "values")[0]

    def _set_placeholder(self):
        self.hotkey_input.delete(0, tk.END)
        self.hotkey_input.insert(0, PLACEHOLDER)

    def _on_function_changed(self, *_):
        if self.function_combo.get() == FUNC_TEXT:
            self.clicker_frame.pack_forget()
            self.text_frame.pack(fill=tk.X, pady=2)
        else:
            self.text_frame.pack_forget()
            self.clicker_frame.pack(fill=tk.X, pady=2)

    def _toggle_restrict(self):
        if self.restrict_var.get():
            self.restrict_frame.pack(fill=tk.X, before=self.add_btn, pady=(4, 0))
        else:
            self.restrict_frame.pack_forget()

    def _on_hotkey_click(self, _event):
        if not self.recording_hotkey:
            self.start_recording_hotkey()
        return "break"

    def start_recording_hotkey(self):
        self.recording_hotkey = True
        self.current_hotkey = []
        self.hotkey_input.delete(0, tk.END)
        self.hotkey_input.insert(0, RECORDING_HINT)
        self._press_hook = keyboard.on_press(self._on_key_press)
        self._release_hook = keyboard.on_release(self._on_key_release)

    def stop_recording_hotkey(self):
        self.recording_hotkey = False
        for hook in (self._press_hook, self._release_hook):
            if hook is not None:
                try:
                    keyboard.unhook(hook)
                except Exception:
                    pass
        self._press_hook = self._release_hook = None
        self.hotkey_input.delete(0, tk.END)
        if self.current_hotkey:
            self.hotkey_input.insert(0, "+".join(self.current_hotkey))
        else:
            self._set_placeholder()

    def _on_key_press(self, event):
        if not self.recording_hotkey:
            return
        key = event.name
        if key == "esc":
            self.current_hotkey = []
            self.after(0, self.stop_recording_hotkey)
            return
        if key not in self.current_hotkey:
            self.current_hotkey.append(key)
        text = "+".join(self.current_hotkey)
        self.after(0, lambda t=text: self.set_hotkey_text(t))

    def _on_key_release(self, event):
        if not self.recording_hotkey:
            return
        if event.name in ("ctrl", "alt", "shift", "windows"):
            self.after(80, self._finish_if_ready)

    def _finish_if_ready(self):
        if not self.recording_hotkey:
            return
        if not any(keyboard.is_pressed(m) for m in ("ctrl", "alt", "shift", "windows")):
            if self.current_hotkey:
                self.stop_recording_hotkey()

    def set_add_hotkey_callback(self, callback):
        self.add_btn.configure(command=callback)

    def set_remove_hotkey_callback(self, callback):
        self.remove_hotkey_callback = callback

    def set_configure_hotkey_callback(self, callback):
        self.configure_hotkey_callback = callback

    def _delete_selected(self):
        hotkey = self._selected_hotkey()
        if not hotkey or not self.remove_hotkey_callback:
            messagebox.showwarning("Warning", "Please select a hotkey first.")
            return
        if messagebox.askyesno("Delete", f'Remove hotkey "{hotkey}"?'):
            self.remove_hotkey_callback(hotkey)

    def _configure_selected(self):
        hotkey = self._selected_hotkey()
        if not hotkey:
            messagebox.showwarning("Warning", "Please select a hotkey first.")
            return
        if not self.adapter:
            return

        data = self.adapter.hotkey_manager.get_hotkey(hotkey)
        if not data:
            return
        if data.get("type") != "clicker":
            messagebox.showinfo(
                "Edit",
                "Speed and mode can only be changed for auto-clicker hotkeys.\n"
                "To change a text hotkey, delete it and add it again.",
            )
            return

        current_cps = int(round(1000.0 / data["interval"])) if data.get("interval") else 5
        current_trigger = data.get("trigger", "toggle")

        dialog = tk.Toplevel(self)
        dialog.title("Edit auto-clicker")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text=f"Hotkey:  {hotkey}",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            frame,
            text="The key combination itself cannot be changed here.",
            foreground="gray",
        ).pack(anchor=tk.W, pady=(0, 10))

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Speed", width=8, anchor=tk.W).pack(side=tk.LEFT)
        cps_var = tk.IntVar(value=current_cps)
        ttk.Spinbox(row, from_=1, to=1000, textvariable=cps_var, width=6).pack(
            side=tk.LEFT
        )
        ttk.Label(row, text="clicks per second", foreground="gray").pack(
            side=tk.LEFT, padx=(8, 0)
        )

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Mode", width=8, anchor=tk.W).pack(side=tk.LEFT)
        trigger_var = tk.StringVar(
            value=MODE_HOLD_SHORT if current_trigger == "hold" else MODE_TOGGLE_SHORT
        )
        ttk.Combobox(
            row,
            textvariable=trigger_var,
            values=[MODE_TOGGLE_SHORT, MODE_HOLD_SHORT],
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT)

        hint = ttk.Label(
            frame,
            text=MODE_HOLD if current_trigger == "hold" else MODE_TOGGLE,
            foreground="gray",
        )
        hint.pack(anchor=tk.W, pady=(2, 0))

        def on_mode(_e=None):
            hint.configure(
                text=MODE_HOLD if trigger_var.get() == MODE_HOLD_SHORT else MODE_TOGGLE
            )

        # re-bind via tracing
        def watch(*_):
            on_mode()

        trigger_var.trace_add("write", watch)

        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X, pady=(14, 0))

        def save():
            trigger = "hold" if trigger_var.get() == MODE_HOLD_SHORT else "toggle"
            try:
                cps = int(cps_var.get())
            except (tk.TclError, ValueError):
                messagebox.showwarning(
                    "Error", "Speed must be a whole number.", parent=dialog
                )
                return
            if cps <= 0:
                messagebox.showwarning(
                    "Error", "Speed must be greater than 0.", parent=dialog
                )
                return
            if self.configure_hotkey_callback:
                self.configure_hotkey_callback(hotkey, cps=cps, trigger=trigger)
            dialog.destroy()

        ttk.Button(btns, text="Save", command=save).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(
            side=tk.RIGHT, padx=(0, 6)
        )

        dialog.wait_window()

    @staticmethod
    def _format_action(data) -> str:
        if data["type"] == "text":
            preview = data["data"][:36].replace("\n", " ")
            if len(data["data"]) > 36:
                preview += "…"
            return f'Type "{preview}"'
        cps = 1000.0 / data["interval"] if data.get("interval") else 0
        btn = BUTTON_LABELS.get(data.get("button", "left"), "Left")
        mode = MODE_HOLD_SHORT if data.get("trigger") == "hold" else MODE_TOGGLE_SHORT
        cps_txt = f"{cps:.0f}" if abs(cps - round(cps)) < 0.05 else f"{cps:.1f}"
        return f"{btn}-click · {cps_txt}/s · {mode}"

    @staticmethod
    def _format_status(data, running: bool) -> str:
        if data["type"] == "text":
            return "Ready"
        if running:
            return "Running"
        return "Ready"

    def update_table(self, hotkeys, running=None):
        if running is None:
            running = set()
        self.hotkey_table.delete(*self.hotkey_table.get_children())
        for hotkey, data in hotkeys.items():
            cond = data.get("conditions", {})
            where = "Limited" if cond.get("window_restriction") else "Anywhere"
            self.hotkey_table.insert(
                "",
                tk.END,
                values=(
                    hotkey,
                    self._format_action(data),
                    where,
                    self._format_status(data, hotkey in running),
                ),
            )

    def get_hotkey_input_text(self):
        text = self.hotkey_input.get().strip()
        if text in (PLACEHOLDER, RECORDING_HINT):
            return ""
        return text

    def get_function_type(self):
        return self.function_combo.get()

    def get_text_input(self):
        return self.text_input.get("1.0", tk.END).strip()

    def get_cps_value(self):
        return int(self.cps_var.get())

    def get_button_value(self):
        label = self.button_combo.get()
        return BUTTON_CODES.get(label, "left")

    def get_trigger_mode(self):
        return "hold" if self.mode_combo.get() == MODE_HOLD_SHORT else "toggle"

    def clear_inputs(self):
        self._set_placeholder()
        self.text_input.delete("1.0", tk.END)
        self.function_combo.set(FUNC_CLICKER)
        self.cps_var.set(5)
        self.button_combo.set("Left")
        self.mode_combo.set(MODE_TOGGLE_SHORT)
        self.hold_var.set(False)
        self.mode_hint.configure(text=MODE_TOGGLE)
        self.restrict_var.set(False)
        self.allowed_windows_list.delete(0, tk.END)
        self.allowed_processes_list.delete(0, tk.END)
        self.restrict_frame.pack_forget()
        self._on_function_changed()

    def set_hotkey_text(self, text):
        self.hotkey_input.delete(0, tk.END)
        self.hotkey_input.insert(0, text)

    def get_window_restrictions(self):
        return {
            "window_restriction": self.restrict_var.get(),
            "allowed_windows": list(self.allowed_windows_list.get(0, tk.END)),
            "allowed_processes": list(self.allowed_processes_list.get(0, tk.END)),
        }

    def add_allowed_window(self):
        if not self.adapter:
            return
        windows = self.adapter.get_active_windows()
        if not windows:
            messagebox.showinfo("Info", "No open windows found.")
            return
        choices = [f"{w['title']} ({w['process_name']})" for w in windows.values()]
        title = simpledialog.askstring(
            "Add window",
            "Type part of the window title (examples below):\n\n"
            + "\n".join(choices[:12]),
        )
        if title:
            self.allowed_windows_list.insert(tk.END, title.split(" (")[0])

    def remove_allowed_window(self):
        sel = self.allowed_windows_list.curselection()
        if sel:
            self.allowed_windows_list.delete(sel[0])

    def add_allowed_process(self):
        if not self.adapter:
            return
        processes = self.adapter.get_process_list()
        if not processes:
            messagebox.showinfo("Info", "No processes found.")
            return
        names = [f"{p['name']} (PID: {p['pid']})" for p in processes[:40]]
        name = simpledialog.askstring(
            "Add process",
            "Type the process name (examples below):\n\n" + "\n".join(names[:12]),
        )
        if name:
            self.allowed_processes_list.insert(tk.END, name.split(" (")[0])

    def remove_allowed_process(self):
        sel = self.allowed_processes_list.curselection()
        if sel:
            self.allowed_processes_list.delete(sel[0])
