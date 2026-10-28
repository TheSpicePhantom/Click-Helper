"""
Hotkey-Tab – Kontextmenü statt Import/Export.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import keyboard

PLACEHOLDER = "Klicken zum Aufnehmen…"


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

    def _build(self):
        form = ttk.LabelFrame(self, text="Neuer Hotkey", padding=8)
        form.pack(fill=tk.X, padx=4, pady=4)

        row = ttk.Frame(form)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Hotkey:").pack(side=tk.LEFT)
        self.hotkey_input = ttk.Entry(row)
        self.hotkey_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self._set_placeholder()
        self.hotkey_input.bind("<Button-1>", self._on_hotkey_click)

        row = ttk.Frame(form)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Funktion:").pack(side=tk.LEFT)
        self.function_combo = ttk.Combobox(
            row, values=["Text eingeben", "Auto-Clicker"], state="readonly", width=18
        )
        self.function_combo.set("Auto-Clicker")
        self.function_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.function_combo.bind("<<ComboboxSelected>>", self._on_function_changed)

        self.text_frame = ttk.Frame(form)
        ttk.Label(self.text_frame, text="Text:").pack(anchor=tk.W)
        self.text_input = tk.Text(self.text_frame, height=2)
        self.text_input.pack(fill=tk.X)

        self.clicker_frame = ttk.Frame(form)
        cps_row = ttk.Frame(self.clicker_frame)
        cps_row.pack(fill=tk.X, pady=2)
        ttk.Label(cps_row, text="CPS:").pack(side=tk.LEFT)
        self.cps_var = tk.IntVar(value=5)
        ttk.Spinbox(cps_row, from_=1, to=1000, textvariable=self.cps_var, width=8).pack(
            side=tk.LEFT, padx=(8, 12)
        )
        ttk.Label(cps_row, text="Button:").pack(side=tk.LEFT)
        self.button_combo = ttk.Combobox(
            cps_row, values=["left", "right", "middle"], state="readonly", width=8
        )
        self.button_combo.set("left")
        self.button_combo.pack(side=tk.LEFT, padx=(8, 0))

        self.hold_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.clicker_frame,
            text="Nur halten (klicken solange Taste gedrückt)",
            variable=self.hold_var,
        ).pack(anchor=tk.W, pady=(4, 0))

        self.restrict_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form,
            text="Nur in bestimmten Fenstern",
            variable=self.restrict_var,
            command=self._toggle_restrict,
        ).pack(anchor=tk.W, pady=(6, 0))

        self.restrict_frame = ttk.Frame(form)
        lists = ttk.Frame(self.restrict_frame)
        lists.pack(fill=tk.X)
        left = ttk.Frame(lists)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        right = ttk.Frame(lists)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="Fenster").pack(anchor=tk.W)
        self.allowed_windows_list = tk.Listbox(left, height=3)
        self.allowed_windows_list.pack(fill=tk.X)
        ttk.Button(left, text="+ Fenster", command=self.add_allowed_window).pack(
            side=tk.LEFT, pady=2
        )
        ttk.Button(left, text="−", command=self.remove_allowed_window).pack(
            side=tk.LEFT, padx=4, pady=2
        )

        ttk.Label(right, text="Prozesse").pack(anchor=tk.W)
        self.allowed_processes_list = tk.Listbox(right, height=3)
        self.allowed_processes_list.pack(fill=tk.X)
        ttk.Button(right, text="+ Prozess", command=self.add_allowed_process).pack(
            side=tk.LEFT, pady=2
        )
        ttk.Button(right, text="−", command=self.remove_allowed_process).pack(
            side=tk.LEFT, padx=4, pady=2
        )

        self.add_btn = ttk.Button(form, text="Hotkey hinzufügen")
        self.add_btn.pack(pady=8)

        list_frame = ttk.LabelFrame(
            self, text="Aktive Hotkeys (Rechtsklick: Konfigurieren / Löschen)", padding=8
        )
        list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        cols = ("hotkey", "function", "conditions", "status")
        self.hotkey_table = ttk.Treeview(list_frame, columns=cols, show="headings", height=8)
        self.hotkey_table.heading("hotkey", text="Hotkey")
        self.hotkey_table.heading("function", text="Funktion")
        self.hotkey_table.heading("conditions", text="Bedingungen")
        self.hotkey_table.heading("status", text="Status")
        self.hotkey_table.column("hotkey", width=110)
        self.hotkey_table.column("function", width=200)
        self.hotkey_table.column("conditions", width=120)
        self.hotkey_table.column("status", width=90)
        self.hotkey_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.hotkey_table.yview)
        self.hotkey_table.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(label="Konfigurieren", command=self._configure_selected)
        self._context_menu.add_command(label="Löschen", command=self._delete_selected)
        self.hotkey_table.bind("<Button-3>", self._on_right_click)
        self.hotkey_table.bind("<Double-1>", lambda e: self._configure_selected())

        self._on_function_changed()

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
        if self.function_combo.get() == "Text eingeben":
            self.clicker_frame.pack_forget()
            self.text_frame.pack(fill=tk.X, pady=2)
        else:
            self.text_frame.pack_forget()
            self.clicker_frame.pack(fill=tk.X, pady=2)

    def _toggle_restrict(self):
        if self.restrict_var.get():
            self.restrict_frame.pack(fill=tk.X, pady=4)
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
        self.hotkey_input.insert(0, "Tasten drücken… (ESC abbrechen)")
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
            messagebox.showwarning("Warnung", "Bitte Hotkey auswählen.")
            return
        if messagebox.askyesno("Löschen", f"Hotkey „{hotkey}“ wirklich löschen?"):
            self.remove_hotkey_callback(hotkey)

    def _configure_selected(self):
        hotkey = self._selected_hotkey()
        if not hotkey:
            messagebox.showwarning("Warnung", "Bitte Hotkey auswählen.")
            return
        if not self.adapter:
            return

        data = self.adapter.hotkey_manager.get_hotkey(hotkey)
        if not data:
            return
        if data.get("type") != "clicker":
            messagebox.showinfo(
                "Konfigurieren",
                "CPS und Umschalten/Halten gelten nur für Auto-Clicker.",
            )
            return

        current_cps = int(round(1000.0 / data["interval"])) if data.get("interval") else 5
        current_trigger = data.get("trigger", "toggle")

        dialog = tk.Toplevel(self)
        dialog.title(f"Konfigurieren: {hotkey}")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"Hotkey: {hotkey} (unveränderlich)").pack(anchor=tk.W, pady=(0, 8))

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="CPS:").pack(side=tk.LEFT)
        cps_var = tk.IntVar(value=current_cps)
        ttk.Spinbox(row, from_=1, to=1000, textvariable=cps_var, width=8).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Modus:").pack(side=tk.LEFT)
        trigger_var = tk.StringVar(
            value="Halten" if current_trigger == "hold" else "Umschalten"
        )
        ttk.Combobox(
            row,
            textvariable=trigger_var,
            values=["Umschalten", "Halten"],
            state="readonly",
            width=14,
        ).pack(side=tk.LEFT, padx=(8, 0))

        btns = ttk.Frame(frame)
        btns.pack(fill=tk.X, pady=(12, 0))

        def save():
            trigger = "hold" if trigger_var.get() == "Halten" else "toggle"
            try:
                cps = int(cps_var.get())
            except (tk.TclError, ValueError):
                messagebox.showwarning("Fehler", "CPS muss eine Zahl sein.", parent=dialog)
                return
            if cps <= 0:
                messagebox.showwarning("Fehler", "CPS muss > 0 sein.", parent=dialog)
                return
            if self.configure_hotkey_callback:
                self.configure_hotkey_callback(hotkey, cps=cps, trigger=trigger)
            dialog.destroy()

        ttk.Button(btns, text="Speichern", command=save).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Abbrechen", command=dialog.destroy).pack(
            side=tk.RIGHT, padx=(0, 6)
        )

        dialog.wait_window()

    def update_table(self, hotkeys, running=None):
        if running is None:
            running = set()
        self.hotkey_table.delete(*self.hotkey_table.get_children())
        for hotkey, data in hotkeys.items():
            if data["type"] == "text":
                func = f"Text: {data['data'][:40]}"
                status = "Bereit"
            else:
                cps = 1000.0 / data["interval"] if data.get("interval") else 0
                trigger = data.get("trigger", "toggle")
                mode = "Halten" if trigger == "hold" else "Umschalten"
                func = f"Clicker {cps:.1f} CPS / {data.get('button', 'left')} / {mode}"
                if hotkey in running:
                    status = "Aktiv"
                elif trigger == "hold":
                    status = "Halten"
                else:
                    status = "Gestoppt"
            cond = data.get("conditions", {})
            cond_txt = "Eingeschränkt" if cond.get("window_restriction") else "Immer"
            self.hotkey_table.insert(
                "", tk.END, values=(hotkey, func, cond_txt, status)
            )

    def get_hotkey_input_text(self):
        text = self.hotkey_input.get().strip()
        if text in (PLACEHOLDER, "Tasten drücken… (ESC abbrechen)"):
            return ""
        return text

    def get_function_type(self):
        return self.function_combo.get()

    def get_text_input(self):
        return self.text_input.get("1.0", tk.END).strip()

    def get_cps_value(self):
        return int(self.cps_var.get())

    def get_button_value(self):
        return self.button_combo.get()

    def get_trigger_mode(self):
        return "hold" if self.hold_var.get() else "toggle"

    def clear_inputs(self):
        self._set_placeholder()
        self.text_input.delete("1.0", tk.END)
        self.function_combo.set("Auto-Clicker")
        self.hold_var.set(False)
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
            messagebox.showinfo("Info", "Keine Fenster gefunden.")
            return
        choices = [f"{w['title']} ({w['process_name']})" for w in windows.values()]
        title = simpledialog.askstring(
            "Fenster", "Titel eingeben:\n" + "\n".join(choices[:12])
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
            messagebox.showinfo("Info", "Keine Prozesse gefunden.")
            return
        names = [f"{p['name']} (PID: {p['pid']})" for p in processes[:40]]
        name = simpledialog.askstring("Prozess", "Name eingeben:\n" + "\n".join(names[:12]))
        if name:
            self.allowed_processes_list.insert(tk.END, name.split(" (")[0])

    def remove_allowed_process(self):
        sel = self.allowed_processes_list.curselection()
        if sel:
            self.allowed_processes_list.delete(sel[0])
