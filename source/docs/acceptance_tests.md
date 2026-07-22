# Acceptance Test Checklist

Run on the Windows target before go-live. Each item maps to a PRD functional
requirement (FR) and a module (M). Mark Pass/Fail and note observations.

## Setup / Platform
- [ ] `scripts\run_windows.bat` completes; console opens at http://127.0.0.1:8080 (M02)
- [ ] `data\omr.db` is created with all tables; app restarts cleanly (M03)
- [ ] `config.yaml` changes (port, dropzone path) take effect after restart (M02)

## Template & Path Layouts (FR-1.3, M04)
- [ ] Calibrator loads the 150Q seed and shows the warped backdrop + bubble overlay
- [ ] Adjusting origin/gap moves the overlay; Save creates a reusable path layout
- [ ] Validation rejects a question count above the family max
- [ ] (When available) 60Q sample registers as a second family

## Exam Programs & Sessions (FR-1.1, FR-1.4, M05)
- [ ] Create a program; add Session 1 (e.g. 20Q) → global range Q1–Q20
- [ ] Add Session 2 (e.g. 30Q) → auto-suggested start Q21, range Q21–Q50
- [ ] Overlapping global range is rejected
- [ ] Subject splits can be added and appear in exports

## Answer Key (FR-1.2, M06)
- [ ] Manual grid entry saves the session slice; coverage map updates
- [ ] CSV upload (cols `question_no,correct_option`) imports the slice
- [ ] Excel (.xlsx) upload works
- [ ] Editing an answer records an audit entry
- [ ] Upload outside the session range is rejected

## Ingestion (FR-2.1, M07)
- [ ] Start ingestion for a session; dropping a JPG/TIFF triggers processing
- [ ] Re-dropping the same file is ignored (SHA-256 dedup)
- [ ] A partially-written file isn't read until stable
- [ ] (If used) PDF expands to per-page images

## Batch Processing (FR-2.1, M08)
- [ ] Batch cannot start while the key slice is incomplete
- [ ] Progress advances to 100%; status ends `completed` or `needs_verification`
- [ ] WebSocket progress updates live in the UI

## OMR Read (FR-2.2, FR-2.3, FR-3.1, M09)
- [ ] Sheets align via corner markers (warp succeeds)
- [ ] Roll number decodes from the bubble matrix (barcode ignored)
- [ ] Single marks read correctly; blanks and multi-marks are flagged
- [ ] Only the session's global question range is scored
- [ ] **Accuracy benchmark**: ≥ target % on a labeled set of real filled scans

## Verification (FR-3.2, M10)
- [ ] Flagged anomalies appear in the queue with crop images
- [ ] Global `L` key focuses the override; A/B/C/D/Blank + Enter confirm
- [ ] Confirm updates the sheet result and recomputes counts
- [ ] Skip/Flag work; batch flips to `completed` when queue is cleared

## Scoring & Export (FR-4.1–4.3, M11/M12)
- [ ] Scores show correct/wrong/blank/multi, Percentage, Secure Score
- [ ] Secure Score excludes blank/multi from the denominator
- [ ] Subject-wise columns are correct
- [ ] Per-session export (CSV + Excel) in literal and binary modes
- [ ] Cumulative program export merges sessions by roll number

## Operations
- [ ] `scripts\backup_db.bat` creates a timestamped backup and prunes old ones
- [ ] Scheduled Task runs the backup nightly
- [ ] Restore-from-backup verified (stop app, swap db, restart)
- [ ] Full offline run confirmed (disconnect network after first install)
