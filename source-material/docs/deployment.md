# Deployment Guide (Windows, On-Premises)

The system runs entirely offline on a single Windows machine. No licensing, no
internet required after first-time dependency install.

## 1. Prerequisites

Install once on the target machine:

- **Python 3.10+** — https://www.python.org/downloads/ (check "Add python.exe to PATH").
- **Node.js LTS** — https://nodejs.org/ (only needed to build the operator console once).
- **Poppler** (optional) — only if you scan to **PDF**. Download Poppler for Windows,
  unzip, and add its `bin\` folder to `PATH`. JPG/TIFF input needs nothing extra.

> First run needs internet to download Python/Node packages. After that it runs
> fully offline.

## 2. Install & run

```
scripts\run_windows.bat
```

This will:
1. Create the Python virtual environment (`.venv`).
2. Install backend dependencies.
3. Build the operator console (first run only).
4. Create `data\`, `data\crops\`, `data\backups\`, and the dropzone folder.
5. Start the server at http://127.0.0.1:8080 and open it in the browser.

To stop: press `Ctrl+C` in the console window.

## 3. Configuration

Edit `config.yaml` (no restart-safe hot reload — restart after changes):

- `server.host` / `server.port` — bind address (default `127.0.0.1:8080`).
- `dropzone.path` — scanner output folder (default `C:\OMR_Dropzone\`).
- `dropzone.accepted_extensions` — file types to ingest.
- `omr.*` — fill/blank/multi thresholds (defaults are sensible; the read pipeline
  also uses a dynamic threshold per sheet).
- `processing.max_workers` — parallelism for batch processing.

## 4. Database & backups

- All data lives in `data\omr.db` (SQLite). Crops for verification are in `data\crops\`.
- Run a nightly backup with `scripts\backup_db.bat` (keeps 30 days in `data\backups\`).
- Schedule it via Task Scheduler:

```
schtasks /create /tn "OMR DB Backup" /tr "C:\path\to\OCRAPP\scripts\backup_db.bat" /sc daily /st 23:30
```

To restore: stop the app, copy a backup over `data\omr.db`, restart.

## 5. Global hotkey (verification)

The `L`-key override works as a global hotkey on Windows out of the box. Start it
from the Verification screen (or `POST /api/verification/hotkey/start`).

## 6. Daily operating flow

1. Create/confirm the **Exam Program** and **Session** (Programs screen).
2. Complete the session's **answer-key slice** (manual grid or CSV/Excel upload).
3. Calibrate the **path layout** once per physical sheet format (Calibrator).
4. Start **ingestion** for the session and scan into the dropzone.
5. Resolve flagged sheets in **Verification**.
6. **Export** per-session or cumulative results (CSV/Excel, literal or binary).

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `Python not found` | Install Python and re-run; ensure "Add to PATH" was checked |
| UI not building | Install Node.js LTS, delete `frontend\dist`, re-run the launcher |
| PDF files ignored | Install Poppler and add its `bin\` to `PATH` |
| Batch won't start ("key incomplete") | Finish the session's answer-key slice first |
| Alignment fails on many sheets | Re-scan at 300 DPI, disable driver deskew, confirm corner markers are visible |
| Wrong bubbles read | Re-calibrate the template in the Calibrator |
| Port in use | Change `server.port` in `config.yaml` |

## 8. Standalone executable (.exe)

The launcher in section 2 needs Python + Node on the machine. To distribute a
**self-contained** build (no Python/Node on the target), produce a one-folder
PyInstaller bundle.

> PyInstaller is **not** a cross-compiler — build on a **Windows** machine. The
> bundle is OS-specific; build once per target Windows architecture.

### Build (on a Windows dev machine, with Python 3.10+ and Node.js LTS)

```
scripts\build_exe.bat
```

This builds the operator console, then runs PyInstaller (`backend\omr.spec`).
Output: `backend\dist\OMR\OMR.exe` plus an `_internal\` folder of bundled
resources (frontend, samples, vendored OMR engine, config default).

### Distribute & run

1. Copy the **entire `backend\dist\OMR` folder** to the target machine (USB/share).
2. Double-click `OMR.exe`. It starts the server and opens a **native desktop window**
   (pywebview with Microsoft Edge WebView2 — included on Windows 10/11).
3. **Close the window** to quit; the server stops and the process exits.
4. Writable data is created **next to the exe**: `OMR\data\` (db, crops, backups).
5. To change settings, drop a `config.yaml` **next to `OMR.exe`** — it overrides the
   bundled default. (Without one, the bundled defaults are used.)

### Notes & limits

- First launch may take a few seconds (large native libs: OpenCV/NumPy/pandas).
- Only one instance can run at a time (a second launch exits quietly).
- PDF input still requires **Poppler** on the target `PATH` (it is not bundled).
- **WebView2** is required for the native window. Windows 10/11 normally include it;
  if the window fails to open, install the
  [WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/).
- The global `L` hotkey works in the bundled app the same as from source.
- If a launch fails with `ModuleNotFoundError`, add the missing package to
  `hiddenimports` in `backend\omr.spec` and rebuild (the vendored engine is loaded
  dynamically, so a new transitive dependency occasionally needs declaring).
- Bundle size is typically ~300–500 MB due to OpenCV/NumPy/pandas/matplotlib.
