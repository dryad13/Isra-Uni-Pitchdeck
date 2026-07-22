# Canon DR-M140 Scanner Setup

This guide configures the Canon imageFORMULA DR-M140 to drop sheet scans directly
into the OMR dropzone so the watcher can pick them up automatically.

## 1. Dropzone folder

The application watches a single folder (default `C:\OMR_Dropzone\`).
It is created automatically by `scripts\run_windows.bat`, or create it manually.

> The path is configured in `config.yaml` under `dropzone.path`. If you change it,
> restart the application.

## 2. Scan profile (CaptureOnTouch / driver settings)

Create a dedicated scan job/profile with these settings:

| Setting | Recommended value | Notes |
|---|---|---|
| Color mode | Grayscale (or Black & White) | Color is unnecessary; grayscale reads faster |
| Resolution | **200–300 DPI** | 300 DPI is the sweet spot for bubble clarity |
| Page size | Match the OMR sheet (A4/Letter) | Auto-size is fine |
| File format | **JPEG** or **TIFF** (single page) | Avoid multi-page TIFF; PDF also supported* |
| Output folder | `C:\OMR_Dropzone\` | Same as the dropzone |
| File naming | Auto-increment (e.g. `scan_0001.jpg`) | Each sheet = one file |
| Deskew / auto-rotate | **Off** | The app warps using the corner markers itself |
| Auto color/blank-page removal | Off | Don't let the driver drop "blank" answer sheets |
| Double-feed detection | On | Prevents stuck/merged sheets |

\* PDF input requires **Poppler** installed and on `PATH` (see `deployment.md`).
Image (JPG/TIFF) input needs no extra software.

## 3. Feed orientation

- Feed sheets so the four **corner bullseye markers** are present and unobstructed.
- Keep the sheet flat; heavy folds near a marker can break alignment.
- The roll-number block and answer grid must be fully within the page.

## 4. Workflow

1. In the operator console, open **Programs**, pick the session, and ensure its
   answer-key slice is **complete** (scanning is blocked otherwise).
2. Start ingestion for that session (Ingestion control / `POST /api/ingestion/start`).
3. Scan a stack into the dropzone. Files are de-duplicated by content hash, so an
   accidental re-scan of the same image is ignored.
4. After a short quiet period the batch auto-starts; watch progress, then resolve
   any flagged sheets in **Verification**.

## 5. Tips

- Calibrate the template once per physical sheet layout in **Calibrator** before
  the first real batch (align the bubble grid to the printed bubbles).
- If alignment fails often, re-check DPI and that markers aren't cropped.
