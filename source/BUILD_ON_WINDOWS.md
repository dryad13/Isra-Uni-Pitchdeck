# Build the OMR System on Windows

This folder is a clean copy of the project for building the standalone
`.exe` on a Windows machine. (No `.venv`, `node_modules`, or build outputs —
those are created fresh here.)

## Prerequisites (install once)

- **Python 3.10+** — https://www.python.org/downloads/ (check "Add python.exe to PATH")
- **Node.js LTS** — https://nodejs.org/
- **Poppler** (only if you scan to PDF) — add its `bin\` to PATH

## Build

Open a Command Prompt in this folder and run:

```
scripts\build_exe.bat
```

This creates a fresh venv, installs deps, builds the operator console, and runs
PyInstaller.

## Result

- Executable: `backend\dist\OMR\OMR.exe`
- Distribute the **entire `backend\dist\OMR` folder** to run elsewhere, or just
  double-click `OMR.exe` here to run on this machine.
- The app opens in a **native desktop window** (pywebview / Edge WebView2). Close
  the window to quit.
- Writable data (`data\` with the SQLite db, crops, backups) is created next to
  the exe on first run.
- To override settings, place a `config.yaml` next to `OMR.exe`.

**WebView2:** The native window needs the Microsoft Edge WebView2 runtime (usually
pre-installed on Windows 10/11). If the window does not appear, install
[WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/).

## If a launch fails with ModuleNotFoundError

The vendored OMR engine loads some dependencies dynamically. If the exe reports a
missing module, add its name to `hiddenimports` in `backend\omr.spec` and rebuild.

See `docs\deployment.md` (section 8) for full details.
