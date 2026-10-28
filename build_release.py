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
LICENSE_NAME = "LICENSE"
README_NAME = "README.txt"


def run(cmd: list[str]) -> None:
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))


def ensure_license() -> Path:
    """LICENSE muss existieren und mit in EXE + ZIP."""
    path = ROOT / LICENSE_NAME
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(
            f"{LICENSE_NAME} fehlt oder ist leer – "
            "ohne Lizenzdatei kein Shipping-Build (Haftungsausschluss)."
        )
    text = path.read_text(encoding="utf-8")
    if "KEINE HAFTUNG" not in text.upper() and "NO WARRANTY" not in text.upper():
        print(
            f"WARNUNG: {LICENSE_NAME} enthält keinen klaren Haftungsausschluss "
            "(KEINE HAFTUNG / NO WARRANTY)."
        )
    print(f"OK Lizenz: {path.name} ({path.stat().st_size} Bytes)")
    return path


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

Portable auto-clicker for Windows (no installation required).

LICENSE / Disclaimer
--------------------
Use of this software is subject to the LICENSE file in this folder
(Click Helper Source-Available License).

THE SOFTWARE IS PROVIDED WITHOUT WARRANTY OF ANY KIND.
The author / copyright holder is not liable for damages, misuse,
or illegal use. Use at your own risk and responsibility.

Full text: LICENSE (German + English)
Repository: https://github.com/TheSpicePhantom/Click-Helper

Start
-----
1. Run ClickHelper.exe
2. If needed: Right-click → Run as administrator
   (global hotkeys on Windows often need admin rights)

Usage
-----
- Record a hotkey and add it
- Right-click a row: Configure / Delete
- Gear (top right): choose folder for hotkeys.json
- GitHub button: source, README, and license online
- X / Minimize: hide to the notification area (tray)
- Ctrl+Q or tray → Exit: quit the app

Data
----
Default: Documents\\Click-Helper\\hotkeys.json
Optional: another folder via the gear (stored next to the EXE).

Version: {VERSION}
"""
    target.write_text(text, encoding="utf-8")


def package_release(exe: Path, license_path: Path) -> Path:
    RELEASE.mkdir(exist_ok=True)
    folder_name = f"ClickHelper-v{VERSION}-portable"
    out_dir = RELEASE / folder_name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    shutil.copy2(exe, out_dir / EXE_NAME)
    shutil.copy2(license_path, out_dir / LICENSE_NAME)
    write_readme(out_dir / README_NAME)

    zip_path = RELEASE / f"{folder_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(out_dir.iterdir()):
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
    print(f"  {EXE_NAME}")
    print(f"  {LICENSE_NAME}   ← Haftungsausschluss / Nutzungsbedingungen")
    print(f"  {README_NAME}")
    print()
    print("Zum Verteilen: ZIP weitergeben – keine Installation nötig.")
    print("LICENSE ist zusätzlich in der EXE eingebettet (PyInstaller datas).")


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
        license_path = ensure_license()
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
        zip_path = package_release(exe, license_path)
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
