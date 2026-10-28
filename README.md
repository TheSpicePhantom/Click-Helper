# Click Helper

Schlanker, portabler Auto-Clicker für Windows.

---

## Hintergrund der Entwicklung

Click Helper ist aus dem Anspruch entstanden, Automatisierung **leichtgewichtig**, **portabel** und **einfach bedienbar** zu halten – ohne den typischen Ballast vieler Tools in diesem Bereich.

Die Leitlinien:

- **Lightweight** – wenig Abhängigkeiten, schnelle Starts, geringer RAM-/CPU-Verbrauch im Hintergrund (Tray).
- **Portable** – eine EXE, keine Installation. USB-Stick und Desktop sind gleichermaßen möglich; der Speicherort der Konfiguration ist frei wählbar.
- **Easy to use** – Hotkey aufnehmen, Funktion wählen, fertig. Keine Account-Pflicht, kein Setup-Assistent, keine Cloud.
- **Keine aufgeblähte Oberfläche** – bewusst keine schwere GUI-Framework-Landschaft (kein PyQt o. Ä.), kein Dashboard-Ballast, keine Overlays in Zielanwendungen. Es gibt nur ein kleines lokales Fenster zur Konfiguration; der eigentliche Nutzen läuft unsichtbar über Hotkeys.
- **Kein Logging** – keine Debug-Protokolle, keine Telemetrie-Dateien, keine Aktivitäts-Historie für Dritte. Was lokal passiert, bleibt lokal und wird nicht dauerhaft mitgeschrieben.
- **Keine Datenweitergabe** – keine Server, keine Analytics, keine Update-Phone-Home-Mechanismen. Hotkeys liegen nur als lokale JSON-Datei auf dem Rechner (oder dort, wohin du den Ordner legst).

### Wie Klicks ausgelöst werden

Mausklicks werden über die **Windows-API** ausgelöst (`win32api.mouse_event` bzw. gleichwertig `ctypes` / `user32`), also als echte Down/Up-Ereignisse auf Systemebene – an der aktuellen Cursorposition.

### Warum so und nicht anders

Bibliotheken wie `pyautogui` sind praktisch, aber für hohe Klickraten spürbar langsamer und schwerfälliger. Direkte Windows-Mausereignisse sind:

- **schneller** und zeitlich präziser (CPS-Kontrolle mit Latenzkompensation),
- **schlanker** (weniger Abstraktionsschichten),
- **näher am System** – geeignet, wenn es um Zuverlässigkeit und niedrige Last geht.

`pyautogui` kommt nur noch dort zum Einsatz, wo es nötig ist (z. B. Text-Hotkeys), nicht für den Kern-Clicker.

### Open Source

Click Helper ist **Open Source**. Der vollständige Quellcode liegt im Repository; Build, Architektur und Verhalten sind nachvollziehbar und anpassbar. Es gibt keinen Closed-Source-Kern und keine versteckten Online-Komponenten.

---

## Was Click Helper kann

| Funktion | Beschreibung |
|----------|--------------|
| **Auto-Clicker** | Linksklick / Rechtsklick / Mittelklick mit einstellbarer CPS |
| **Umschalten oder Halten** | Ein Hotkey startet/stoppt (Toggle) – oder klickt nur, solange die Taste gedrückt bleibt (Hold) |
| **Text-Hotkeys** | Gespeicherter Text wird per Hotkey eingefügt |
| **Fenster-/Prozess-Filter** | Optional nur in bestimmten Fenstern oder Prozessen aktiv |
| **Tray** | X oder Minimieren legt die App in den Infobereich; Strg+Q oder Tray beendet |
| **Portabler Speicherort** | Standard: `Dokumente\Click-Helper`; über das Zahnrad dauerhaft änderbar |

---

## Schnellstart (portable EXE)

1. Release-ZIP entpacken (z. B. `ClickHelper-v1.1.0-portable.zip`).
2. `ClickHelper.exe` starten.
3. Bei Bedarf: **Rechtsklick → Als Administrator ausführen** (globale Hotkeys brauchen unter Windows oft Admin-Rechte).

Keine Installation, kein Installer nötig.

Gebaut wird die portable Variante so:

```bash
python build_release.py
```

Ergebnis:

- `dist/ClickHelper.exe`
- `release/ClickHelper-v1.1.0-portable.zip`

---

## Bedienung

### Hotkey anlegen

1. Ins Hotkey-Feld klicken und die gewünschte Tastenkombination drücken (ESC bricht ab).
2. Funktion wählen: **Auto-Clicker** oder **Text eingeben**.
3. Bei Auto-Clicker: CPS, Maustaste, optional **Nur halten**.
4. Optional: **Nur in bestimmten Fenstern** – Fenster- und/oder Prozesslisten pflegen.
5. **Hotkey hinzufügen**.

Doppelbelegungen sind nicht erlaubt (`Ctrl+X` und `ctrl+x` gelten als dieselbe Kombination).

### Hotkeys verwalten

In der Liste:

- **Rechtsklick** (oder Doppelklick) → **Konfigurieren** / **Löschen**
- **Konfigurieren** (nur Auto-Clicker): CPS und Modus Umschalten/Halten ändern – die Taste selbst bleibt

### Zahnrad (Speicherort)

Oben rechts **⚙**:

- aktuellen Ordner für `hotkeys.json` sehen
- **Ordner ändern…** – neuer Pfad wird dauerhaft gespeichert (portable Einstellung neben der EXE: `click_helper_settings.json`)
- **Im Explorer öffnen**
- **Standard** – zurück auf `Dokumente\Click-Helper`

### Tray und Beenden

| Aktion | Ergebnis |
|--------|----------|
| Fenster schließen (X) | App bleibt im Tray |
| Minimieren | App geht in den Tray |
| Tray-Linksklick / Menü „Anzeigen“ | Fenster wieder sichtbar |
| Tray „Beenden“ oder **Strg+Q** | Anwendung beenden |

---

## Daten und Privatsphäre

| Datei / Ort | Inhalt |
|-------------|--------|
| `Dokumente\Click-Helper\hotkeys.json` (oder gewählter Ordner) | Deine Hotkey-Konfiguration |
| `click_helper_settings.json` (neben der EXE) | Optionaler Verweis auf den Datenordner |

Es werden **keine** Nutzungsstatistiken, Screenshots, Fensterinhalte oder sonstige Telemetrie erhoben oder versendet. Offline-First.

---

## Architektur (kurz)

MVA-Struktur in Python:

```
main.py
├── model/      # Hotkeys, Clicker-Thread, Prozesse, Settings
├── view/       # tkinter-Fenster, Tray, UI-Dispatch
└── adapter/    # Verknüpfung View ↔ Model, Hotkey-Registrierung
```

Technischer Stack (Runtime):

- **tkinter** – minimale Konfigurations-UI (mit Python mitgeliefert)
- **keyboard** – globale Hotkeys
- **pywin32** – schnelle Mausklicks und Tray
- **psutil** – Prozesslisten für optionale Filter
- **pyautogui** – nur Text-Eingabe

---

## Von Quellcode starten

Voraussetzungen: Windows 10/11, Python 3.10+ (empfohlen).

```bash
git clone <repository-url>
cd Click-Helper
pip install -r requirements.txt
python main.py
```

Release bauen:

```bash
python build_release.py
# oder ohne erneutes pip:
python build_release.py --skip-deps
```

---

## Hinweise und Grenzen

- Globale Hotkeys und zuverlässige Klicks funktionieren unter Windows oft nur mit **Administratorrechten**.
- Sehr hohe CPS-Werte belasten die CPU stärker und können in Spielen oder Tools unerwünscht sein – bewusst und verantwortungsvoll nutzen.
- Fensterfilter prüfen den Vordergrund; sie ersetzen keine Anticheat- oder Sicherheitslogik von Drittsoftware.
- Click Helper ist ein lokales Hilfsprogramm, kein „Cheat-Framework“ und kein Cloud-Dienst.

---

## Mitwirken / Open Source

Verbesserungen, Bugfixes und Ideen sind willkommen. Der Code ist offen einsehbar und soll nachvollziehbar bleiben: wenig Magie, klare Schichten, portable Distribution.

---

## Lizenz

Open Source – siehe Repository-Lizenzdatei, sofern vorhanden. Nutzung auf eigene Verantwortung.
