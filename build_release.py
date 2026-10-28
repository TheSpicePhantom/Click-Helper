#!/usr/bin/env python3
"""
Click Helper – Shipping-Build
Erzeugt eine portable Onefile-EXE und ein Release-ZIP.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = "1.1.0"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
RELEASE = ROOT / "release"
SPEC = ROOT / "ClickHelper.spec"
EXE_NAME = "ClickHelper.exe"


def run(cmd: list[str]) -> None:
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))


def ensure_deps(with_pillow: bool = True) -> None:
    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    if with_pillow:
        run([sys.executable, "-m", "pip", "install", "Pillow"])


def ensure_icon_ico() -> None:
    ico = ROOT / "icon.ico"
    png = ROOT / "icon.png"
    if ico.exists() and ico.stat().st_size > 0:
        print(f"OK Icon: {ico.name}")
        return
    if not png.exists():
        raise FileNotFoundError("icon.png fehlt – für den Build benötigt.")
    try:
        from PIL import Image

        img = Image.open(png)
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(ico, format="ICO", sizes=sizes)
        print(f"OK Icon erzeugt: {ico.name}")
    except Exception as e:
        raise RuntimeError(f"icon.ico konnte nicht erzeugt werden: {e}") from e


def clean() -> None:
    for path in (DIST / EXE_NAME,):
        if path.exists():
            path.unlink()
    # Alte Minimal-EXE nicht mitliefern
    old = DIST / "ClickHelper-Minimal.exe"
    if old.exists():
        old.unlink()
        print("Alte ClickHelper-Minimal.exe entfernt")


def build_exe() -> Path:
    if not SPEC.exists():
        raise FileNotFoundError(f"{SPEC.name} fehlt")
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(SPEC),
            "--noconfirm",
            "--clean",
        ]
    )
    exe = DIST / EXE_NAME
    if not exe.exists():
        raise FileNotFoundError(f"Build fehlgeschlagen – {exe} nicht gefunden")
    return exe


def write_readme(target: Path) -> None:
    text = f"""Click Helper v{VERSION}
====================

Portable Auto-Clicker für Windows (keine Installation nötig).

Start
-----
1. ClickHelper.exe starten
2. Bei Bedarf: Rechtsklick → Als Administrator ausführen
   (globale Hotkeys brauchen oft Admin-Rechte)

Bedienung
---------
- Hotkey aufnehmen und hinzufügen
- Rechtsklick auf Eintrag: Konfigurieren / Löschen
- Zahnrad oben rechts: Speicherort für hotkeys.json wählen
- X / Minimieren: in den Infobereich (Tray)
- Strg+Q oder Tray → Beenden: App beenden

Daten
-----
Standard: Dokumente\\Click-Helper\\hotkeys.json
Optional: anderer Ordner über das Zahnrad (wird neben der EXE gemerkt).

Version: {VERSION}
"""
    target.write_text(text, encoding="utf-8")


def package_release(exe: Path) -> Path:
    RELEASE.mkdir(exist_ok=True)
    folder_name = f"ClickHelper-v{VERSION}-portable"
    out_dir = RELEASE / folder_name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    shutil.copy2(exe, out_dir / EXE_NAME)
    write_readme(out_dir / "README.txt")

    zip_path = RELEASE / f"{folder_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in out_dir.iterdir():
            zf.write(file, arcname=f"{folder_name}/{file.name}")

    return zip_path


def print_summary(exe: Path, zip_path: Path) -> None:
    size_mb = exe.stat().st_size / (1024 * 1024)
    zip_mb = zip_path.stat().st_size / (1024 * 1024)
    print()
    print("=" * 50)
    print("Shipping-Build fertig")
    print("=" * 50)
    print(f"EXE : {exe}  ({size_mb:.1f} MB)")
    print(f"ZIP : {zip_path}  ({zip_mb:.1f} MB)")
    print()
    print("Inhalt ZIP:")
    print("  ClickHelper.exe")
    print("  README.txt")
    print()
    print("Zum Verteilen: ZIP weitergeben – keine Installation nötig.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Click Helper Shipping-Build")
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="pip install überspringen",
    )
    parser.add_argument(
        "--no-clean-build",
        action="store_true",
        help="PyInstaller --clean weglassen (nur für schnelle Tests)",
    )
    args = parser.parse_args()

    print(f"Click Helper Shipping-Build v{VERSION}")
    print("=" * 50)

    try:
        if not args.skip_deps:
            ensure_deps()
        ensure_icon_ico()
        clean()
        if args.no_clean_build:
            # Spec-Build ohne extra clean-Flag – trotzdem noconfirm
            run([sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm"])
            exe = DIST / EXE_NAME
            if not exe.exists():
                raise FileNotFoundError(exe)
        else:
            exe = build_exe()
        zip_path = package_release(exe)
        print_summary(exe, zip_path)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"FEHLER: Befehl fehlgeschlagen (Exit {e.returncode})")
        return e.returncode or 1
    except Exception as e:
        print(f"FEHLER: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
