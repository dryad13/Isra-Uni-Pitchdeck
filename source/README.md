# OMR Console — application source

Editable source for the on-premises **OMR Console** (React frontend + FastAPI backend).

This is what you clone and develop on a new laptop. The packaged Windows demo (`OMR.exe`) lives in `../app/`.

## Setup (dev)

1. Install **Python 3.10+**, **Node.js 20+**, and Git.
2. From this folder:
   - Frontend: `cd frontend && npm install && npm run dev`
   - Backend: see `scripts/run_windows.bat` or `BUILD_ON_WINDOWS.md`
3. Config: `config.yaml` (dropzone path, ports, etc.)

## Key paths

| Path | Role |
|------|------|
| `frontend/` | React / Vite operator UI |
| `backend/` | FastAPI + OMR pipeline |
| `scripts/run_windows.bat` | Local Windows launcher |
| `samples/` | Isra sheet templates |
| `docs/` | Deployment / Canon / acceptance |
| `context.md` | Product / module bible |

## Demo package

To run without building: use `../app/NEW 2 - Launch OMR (no black window).vbs`.