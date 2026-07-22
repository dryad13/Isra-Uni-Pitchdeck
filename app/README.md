# OMR Console — Demo App

Windows demo package for **OMR Console** (Isra University).

> The large `OMR-Demo.zip` is **not** included (over GitHub’s 100 MB file limit).
> The extracted `OMR\` folder is already in this repo — you can launch without extracting.

## Quick start (recommended)

1. Copy this whole `app` folder to the demo laptop Desktop (do **not** run from USB/network alone if antivirus is aggressive).
2. If needed, run `Install VC++ Runtime.bat` once (`vc_redist.x64.exe` included).
3. Double-click **`NEW 2 - Launch OMR (no black window).vbs`**
4. When finished, close the OMR window or run **`NEW 3 - Stop OMR.bat`**

## Alternate simple launchers

| File | Purpose |
|------|---------|
| `START.vbs` | Same idea as NEW 2 — desktop window, no black console |
| `STOP-simple.bat` | Emergency stop |
| `SETUP.bat` | Only needed if `OMR\OMR.exe` is missing **and** you have `OMR-Demo.zip` locally |

## Also included

- `Diagnose System.bat` / `Verify Package.bat`
- `DemoScans\` — sample images for a live scan demo (drop into the app dropzone while ingestion is active)
- `OMR\` — packaged `OMR.exe` + runtime (PyInstaller)

Logs: `OMR\data\omr.log`

See `00 READ ME FIRST - NEW.txt` and `HOW TO USE.txt` for full demo notes.
