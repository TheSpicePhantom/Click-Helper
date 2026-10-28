# Click Helper

**[Deutsch](README.md)** · English

Lightweight, portable auto-clicker for Windows.

Repository: https://github.com/TheSpicePhantom/Click-Helper

---

## Background

Click Helper was built to keep automation **lightweight**, **portable**, and **easy to use** — without the usual bloat of many tools in this space.

Design goals:

- **Lightweight** – few dependencies, fast startup, low RAM/CPU while running in the tray.
- **Portable** – one EXE, no installer. USB stick and desktop both work; the config folder is freely choosable.
- **Easy to use** – record a hotkey, pick a function, done. No account, no setup wizard, no cloud.
- **No bloated UI** – deliberately no heavy GUI stack (no PyQt etc.), no dashboard clutter, no overlays in target apps. There is only a small local window for configuration; real use happens invisibly via hotkeys.
- **No logging** – no debug logs, no telemetry files, no activity history for third parties. What happens locally stays local and is not written out permanently.
- **No data sharing** – no servers, no analytics, no update phone-home. Hotkeys live only as a local JSON file on your machine (or wherever you place the folder).

### How clicks are triggered

Mouse clicks use the **Windows API** (`win32api.mouse_event` / equivalent `ctypes` / `user32`) as real down/up events at system level — at the current cursor position.

### Why this approach

Libraries like `pyautogui` are convenient but noticeably slower and heavier at high click rates. Direct Windows mouse events are:

- **faster** and more precise in time (CPS control with latency compensation),
- **leaner** (fewer abstraction layers),
- **closer to the system** — better when reliability and low load matter.

`pyautogui` is used only where needed (e.g. text hotkeys), not for the core clicker.

### Source available

The full source code is public in the repository; build, architecture, and behavior are inspectable. There is no closed-source core and no online telemetry.

**Important:** This is intentionally **not** a classic OSI open-source license. Private use: yes. Commercial distribution and sale: no (unless written permission). Changes you redistribute: only as a public fork with a link to the original repository. Details: [LICENSE](LICENSE) (English section included).

---

## Features

| Feature | Description |
|---------|-------------|
| **Auto-clicker** | Left / right / middle click with adjustable CPS |
| **Toggle or hold** | One hotkey starts/stops (toggle) — or clicks only while the key is held (hold) |
| **Text hotkeys** | Stored text is typed/pasted via hotkey |
| **Window / process filter** | Optionally active only in certain windows or processes |
| **Tray** | Close (X) or minimize hides to the notification area; Ctrl+Q or tray exits |
| **Portable data folder** | Default: `Documents\Click-Helper`; permanently changeable via the gear icon |

---

## Quick start (portable EXE)

1. Unpack the release ZIP (e.g. `ClickHelper-v1.1.0-portable.zip`).
2. Run `ClickHelper.exe`.
3. If needed: **Right-click → Run as administrator** (global hotkeys on Windows often need admin rights).

No installation, no installer.

Build the portable package with:

```bash
python build_release.py
```

Output:

- `dist/ClickHelper.exe`
- `release/ClickHelper-v1.1.0-portable.zip`

---

## Usage

### Add a hotkey

1. Click the hotkey field and press the desired key combination (ESC cancels).
2. Choose a function: **Auto-clicker** or **Enter text**.
3. For auto-clicker: CPS, mouse button, optional **Hold only**.
4. Optional: **Only in certain windows** — maintain window and/or process lists.
5. **Add hotkey**.

Duplicate bindings are not allowed (`Ctrl+X` and `ctrl+x` count as the same combination).

### Manage hotkeys

In the list:

- **Right-click** (or double-click) → **Configure** / **Delete**
- **Configure** (auto-clicker only): change CPS and toggle/hold mode — the key itself stays the same

### Gear (storage location)

Top right **⚙**:

- see the current folder for `hotkeys.json`
- **Change folder…** — new path is stored permanently (portable setting next to the EXE: `click_helper_settings.json`)
- **Open in Explorer**
- **Default** — back to `Documents\Click-Helper`

### Tray and exit

| Action | Result |
|--------|--------|
| Close window (X) | App stays in the tray |
| Minimize | App goes to the tray |
| Tray left-click / menu “Show” | Window visible again |
| Tray “Exit” or **Ctrl+Q** | Quit the application |

The header **GitHub** button opens the public repository (source, README, license).

---

## Data and privacy

| File / location | Content |
|-----------------|---------|
| `Documents\Click-Helper\hotkeys.json` (or chosen folder) | Your hotkey configuration |
| `click_helper_settings.json` (next to the EXE) | Optional pointer to the data folder |

No usage statistics, screenshots, window contents, or other telemetry are collected or sent. Offline-first.

---

## Architecture (short)

MVA layout in Python:

```
main.py
├── model/      # Hotkeys, clicker thread, processes, settings
├── view/       # tkinter window, tray, UI dispatch
└── adapter/    # View ↔ model wiring, hotkey registration
```

Runtime stack:

- **tkinter** – minimal configuration UI (ships with Python)
- **keyboard** – global hotkeys
- **pywin32** – fast mouse clicks and tray
- **psutil** – process lists for optional filters
- **pyautogui** – text input only

---

## Run from source

Requirements: Windows 10/11, Python 3.10+ (recommended).

```bash
git clone https://github.com/TheSpicePhantom/Click-Helper.git
cd Click-Helper
pip install -r requirements.txt
python main.py
```

Build a release:

```bash
python build_release.py
# or without reinstalling deps:
python build_release.py --skip-deps
```

---

## Notes and limits

- Global hotkeys and reliable clicks on Windows often need **administrator rights**.
- Very high CPS values increase CPU load and may be unwanted in games or other tools — use deliberately and responsibly.
- Window filters check the foreground window; they do not replace anticheat or third-party security logic.
- Click Helper is a local helper tool, not a “cheat framework” and not a cloud service.

---

## Contributing

Improvements and bugfixes are welcome — please as a **public fork** of  
https://github.com/TheSpicePhantom/Click-Helper  
with a clear link to the original repository. Little magic, clear layers, portable distribution.

---

## License

Click Helper is under the **Click Helper Source-Available License** — see [LICENSE](LICENSE) (German + English).

Short summary (the full license text is authoritative):

| | |
|--|--|
| View source | allowed |
| Private / non-commercial use | allowed |
| Commercial distribution / sale | **forbidden**, except express **written** permission |
| Redistributed changes | only as a **public fork** + link to the original repo |
| Liability for misuse | **none** — use at your own risk |

Original repository: https://github.com/TheSpicePhantom/Click-Helper
