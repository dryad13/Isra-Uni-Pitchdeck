# OMR Exam-Processing System — Codebase Status Report

**Scope:** `spMDTA/windows/` (on-premises OMR platform). Evidence is from files read in this audit only.

---

## 1. Tech stack & architecture

### Frontend

| Item | Value |
|------|--------|
| Framework | React 19 (`frontend/package.json`) |
| Language | TypeScript |
| Routing | `react-router-dom` v7 (`frontend/src/App.tsx`) |
| Build tool | Vite 8 (`frontend/vite.config.ts`, scripts: `dev`, `build`, `preview`) |
| Other libs | Vitest, Testing Library (dev only) |

### Backend

| Item | Value |
|------|--------|
| Framework | FastAPI (`backend/app/main.py`) |
| Language | Python 3 |
| Server | Uvicorn |
| Key libs | SQLAlchemy, Pydantic Settings, PyYAML, Watchdog, pynput, pandas, openpyxl, pdf2image, websockets (`backend/requirements.txt`) |
| Packaging | PyInstaller entry via `backend/desktop.py` + `backend/omr.spec` |

### Database

| Item | Value |
|------|--------|
| Engine | SQLite (default `sqlite:///./data/omr.db`) |
| ORM | SQLAlchemy declarative models in `backend/app/db/models.py` |
| Schema creation | `Base.metadata.create_all()` in `backend/app/db/session.py` — **no migration files / Alembic** found |
| Config | `config.yaml` + env overrides when `OMR_TEST_MODE=1` |

### Computer vision

| Item | Value |
|------|--------|
| Primary library | **OpenCV** via `opencv-python-headless` (unpinned in `requirements.txt`; installed version not recorded in repo) |
| Also used | NumPy, Pillow; vendored **OMRChecker v1.1.0** under `backend/omr_engine/` (`backend/omr_engine/README.md`) |
| Custom pipeline | `backend/app/omr/` (align, threshold, bubbles, roll_number, pipeline, bubble_refine) |

### Repo organization (one paragraph)

`spMDTA/windows/` is a monorepo-style Windows deployment: `backend/app/` holds the FastAPI app (API routers, services, DB models, OMR pipeline, dropzone watcher, hotkey listener); `backend/omr_engine/` is a vendored OMRChecker fork used for template geometry and marker warping; `frontend/src/` is a four-route React operator console; `samples/` (referenced from `backend/app/paths.py`) holds blank templates and seed `template.json` per family; `config.yaml` sits at repo root; runtime data goes under `data/` (DB, crops, PDF pages, backups dir created but unused); `tests/` has Playwright E2E, API clients, and pytest integration tests; `scripts/start_test_server.py` boots an isolated test server.

### How to run

**Dev (inferred from code, no project README at repo root):**

1. Backend: from `backend/`, install `requirements.txt`, then run `app.main` via uvicorn (default host `127.0.0.1`, port **8080** per `config.yaml` and `backend/app/main.py`).
2. Frontend: from `frontend/`, `npm install` then `npm run dev` (Vite on **5173**, proxies `/api` → `8080` per `frontend/vite.config.ts`).
3. Production-ish: build frontend (`npm run build`), then serve via FastAPI static fallback (`backend/app/main.py` mounts `frontend/dist`).

**Frozen Windows build:** `backend/desktop.py` runs uvicorn and opens browser after 3s.

**Test server:** `scripts/start_test_server.py` sets `OMR_TEST_MODE=1`, temp DB/dropzone, port `18080` (or `OMR_TEST_PORT`).

**Config / env:**

| Source | Purpose |
|--------|---------|
| `config.yaml` | server, database, dropzone, omr thresholds (mostly unused in code — see §5), processing, export |
| `OMR_TEST_MODE=1` | Enables test API + config overrides |
| `OMR_DATABASE_URL` | Override SQLite URL in test mode |
| `OMR_DROPZONE_PATH` | Override dropzone path in test mode |
| `OMR_TEST_PORT` | Test server port |

Default dropzone: `C:\OMR_Dropzone\` (`config.yaml`, `backend/app/config.py`).

---

## 2. Pages & screens actually implemented

Four client routes in `frontend/src/App.tsx`:

### `/` — Run exam (`OperatorDashboard/index.tsx` + step components)

| UI | Wired? |
|----|--------|
| Step 1: exam program select/create, session table (radio select, delete), add session form (name, sheet question count, template family) | **Real API:** `/programs`, `/programs/{id}`, `/programs/{id}/sessions`, `/templates/families`, DELETE `/sessions/{id}` |
| Step 2: answer key tabs — upload marked sheet, CSV/XLSX, manual grid (A–D selects per global Q) | **Real API:** `/sessions/{id}/key-status`, POST `/programs/{id}/answer-keys`, upload `/programs/{id}/answer-keys/upload` |
| Step 3: start/stop scan, dropzone stats, scan file upload | **Real API:** `/ingestion/start`, `/stop`, `/status`, `/upload` |
| Footer links to Results / Reports | Navigation only |

**Not wired in UI:** `path_layout_id` always sent as `null` when creating sessions (`OperatorDashboard/index.tsx` line 146). Subject splits, program coverage map, answer-key audit — API exists, no screen.

### `/verify` — Results / verification queue (`VerificationQueue.tsx`)

| UI | Wired? |
|----|--------|
| Pending count lozenge | **Real:** `/verification/pending`; nav badge via `PendingContext` |
| Queue list (roll vs Q# items) | **Real** pending items |
| Crop image, MCQ option buttons or roll text input | **Real:** `/verification/{id}/crop`, POST `/verification/{id}/resolve` |
| Confirm / Skip / Flag buttons | **Real** |
| In-page keyboard: A–D, 0=blank, Enter, S, F | Client-side only, calls resolve API |
| Global L-key start/stop toggle | **Real:** `/verification/hotkey/start\|stop\|status` + WebSocket `/api/ws/verification` |
| Empty state | Shown when queue empty |

### `/export` — Reports (`ExportReport.tsx`)

| UI | Wired? |
|----|--------|
| Program + scope selects (session or whole program) | **Real:** `/programs`, `/programs/{id}/sessions` |
| Mode (literal/binary), format (CSV/XLSX), export button | **Real download:** `/api/sessions/{id}/export` or `/api/programs/{id}/export` |
| Score summary table (roll, correct/wrong/blank/multi, %, secure) | **Real:** `/sessions/{id}/scores` when a session is selected |

### `/advanced/calibrator` — Layout Calibrator (`LayoutCalibrator.tsx`)

| UI | Wired? |
|----|--------|
| Family select, load seed, pick saved layout | **Real:** `/templates/families`, `/families/{family}/seed`, `/templates`, `/templates/{id}` |
| Warped blank + bubble overlay preview | **Real:** POST `/templates/overlay`, `/templates/warp` |
| Numeric editors for bubble size and field-block origin/gaps | Local state → preview refresh |
| Validate, save new / update layout | **Real:** POST `/templates/validate`, POST/PUT `/templates` |

**No other routes.** No roster page, batch detail page, sheet drill-down, settings, or backup UI.

---

## 3. Database schema as built

Defined in `backend/app/db/models.py`, created via `create_all` (no migrations).

### `exam_programs`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| name | String(255) | |
| planned_max_questions | Integer nullable | |
| key_coverage_end | Integer nullable | max covered Q# |
| description | Text nullable | |

**Relations:** → sessions, answer_keys, subject_splits

### `path_layouts`

| Column | Type |
|--------|------|
| id | Integer PK |
| template_family | String(16) |
| name | String(255) |
| max_questions | Integer |
| columns_json | Text nullable — full OMRChecker template JSON |
| roll_number_json | Text nullable — **defined, not populated in services read** |
| anchor_json | Text nullable — **defined, not populated in services read** |
| created_at | DateTime |

### `exam_sessions`

| Column | Type |
|--------|------|
| id | Integer PK |
| program_id | FK → exam_programs |
| template_family | String(16) |
| session_order | Integer |
| name | String(255) |
| path_layout_id | FK → path_layouts nullable |
| sheet_question_count | Integer |
| global_q_start, global_q_end | Integer |
| key_complete | Boolean |
| exam_date | Date nullable |
| batch_name | String nullable |
| export_mode | String(32), default `"literal"` |

### `answer_keys`

| Column | Type |
|--------|------|
| id | Integer PK |
| program_id | FK |
| question_no | Integer |
| correct_option | String(8) |
| added_via_session_id | FK nullable |
| updated_at | DateTime |
| Unique | (program_id, question_no) |

### `answer_key_audit`

| Column | Type |
|--------|------|
| id | Integer PK |
| program_id | FK |
| question_no | Integer |
| old_value, new_value | String(8) nullable |
| changed_by | String(128) nullable |
| changed_at | DateTime |

### `subject_splits`

| Column | Type |
|--------|------|
| id | Integer PK |
| program_id | FK nullable |
| session_id | FK nullable |
| subject_name | String(255) |
| q_start, q_end | Integer |

### `scan_batches`

| Column | Type |
|--------|------|
| id | Integer PK |
| session_id | FK |
| status | String(32), default `"pending"` |
| progress_pct | Float |
| started_at | DateTime nullable |

### `sheet_results`

| Column | Type |
|--------|------|
| id | Integer PK |
| batch_id | FK |
| roll_no | String(32) nullable |
| answers_json | Text nullable — `{global_q: option}` map |
| counts_json | Text nullable — answered/blank/multi + metadata |

**No normalized per-question responses table.**

### `verification_queue`

| Column | Type |
|--------|------|
| id | Integer PK |
| sheet_id | FK |
| global_question_no | Integer (0 for roll anomalies) |
| anomaly_type | String(32) — `multi`, `roll_ambiguous` |
| crop_path | String(512) nullable |
| detected_values | Text nullable |
| resolved_value | String(8) nullable |
| status | String(32), default `"pending"` |

**Overrides live here; no separate overrides table.**

### `ingested_files`

| Column | Type |
|--------|------|
| id | Integer PK |
| file_hash | String(64) unique |
| filename | String(512) |
| session_id | FK nullable |
| processed_at | DateTime nullable |

### Deviations from roll-number / answer-key / responses / overrides model

| Expected concept | Actual |
|------------------|--------|
| Roster | **No table, no column** |
| Responses | **JSON blob** on `sheet_results`, not row-per-question |
| Overrides | **`verification_queue`** only; no operator audit for verification actions |
| Negative marking | **Not in schema or scoring** |
| Per-field confidence | **Not persisted** (only transient in pipeline) |
| Expected scan count / reconciliation | **Not stored** |

---

## 4. Backend / API surface

All routes mounted under `/api` (`backend/app/main.py`).

| Method | Route | Purpose | Status |
|--------|-------|---------|--------|
| GET | `/health` | Liveness JSON | Wired |
| GET | `/templates/families` | List 150Q/60Q families | Wired |
| GET | `/templates/families/{family}/seed` | Seed template JSON | Wired |
| GET | `/templates` | List path layouts | Wired |
| POST | `/templates` | Create layout | Wired |
| GET | `/templates/{layout_id}` | Get layout + template | Wired |
| PUT | `/templates/{layout_id}` | Update layout | Wired |
| DELETE | `/templates/{layout_id}` | Delete layout | Wired |
| POST | `/templates/overlay` | Bubble geometry for calibrator | Wired (needs OMR engine deps) |
| POST | `/templates/warp` | Base64 warped blank image | Wired |
| POST | `/templates/validate` | Template validation | Wired |
| GET | `/programs` | List programs | Wired |
| POST | `/programs` | Create program | Wired |
| GET | `/programs/{id}` | Program + sessions + subjects + coverage | Wired |
| DELETE | `/programs/{id}` | Delete program cascade | Wired |
| GET | `/programs/{id}/coverage` | Key coverage map | Wired |
| GET/POST | `/programs/{id}/subjects` | List/create subject splits | Wired, **no UI** |
| DELETE | `/programs/subjects/{split_id}` | Delete subject split | Wired, **no UI** |
| GET | `/programs/{id}/sessions` | List sessions | Wired |
| GET | `/programs/{id}/sessions/suggest-start` | Next global Q start | Wired |
| POST | `/programs/{id}/sessions` | Create session | Wired |
| GET | `/sessions/{id}` | Session detail | Wired |
| DELETE | `/sessions/{id}` | Delete session | Wired |
| GET | `/programs/{id}/answer-keys` | List keys (optional range) | Wired |
| POST | `/programs/{id}/answer-keys` | Upsert keys + audit | Wired |
| POST | `/programs/{id}/answer-keys/upload` | CSV/XLSX or OMR sheet | Wired |
| POST | `/programs/{id}/answer-keys/from-sheet` | OMR sheet alias | Wired |
| DELETE | `/programs/{id}/answer-keys/{question_no}` | Delete key | Wired, **no UI** |
| GET | `/programs/{id}/answer-keys/audit` | Answer-key change log | Wired, **no UI** |
| GET | `/sessions/{id}/key-status` | Slice readiness for scanning | Wired |
| POST | `/batches/start` | Start background batch | Wired |
| GET | `/batches/{id}` | Batch summary | Wired |
| GET | `/sessions/{id}/batches` | List batches | Wired, **no UI** |
| GET | `/batches/{id}/sheets` | Sheet results JSON | Wired, **no UI** |
| WS | `/ws/batch/{id}` | Batch progress poll | Wired, **no UI consumer found** |
| POST | `/ingestion/start` | Watch dropzone for session | Wired |
| POST | `/ingestion/stop` | Stop watcher | Wired |
| GET | `/ingestion/status` | Watcher stats | Wired |
| POST | `/ingestion/flush` | Manual flush pending → batch | Wired, **no UI button** |
| POST | `/ingestion/upload` | Upload file into dropzone | Wired |
| GET | `/verification/pending` | Pending queue items | Wired |
| GET | `/verification/stats` | Counts by status | Wired, **no UI** |
| GET | `/verification/{id}` | Single item | Wired, **no UI** |
| GET | `/verification/{id}/crop` | PNG crop file | Wired |
| POST | `/verification/{id}/resolve` | confirm/skip/flag | Wired |
| POST | `/verification/hotkey/start\|stop` | Global L listener | Wired |
| GET | `/verification/hotkey/status` | Listener status | Wired |
| WS | `/ws/verification` | Hotkey fan-out | Wired |
| GET | `/sessions/{id}/scores` | Score all sheets in session | Wired |
| GET | `/sessions/{id}/export` | CSV/XLSX download | Wired |
| GET | `/programs/{id}/export` | Cumulative program export | Wired |
| POST | `/test/seed-verification` | Test-only seed | Gated by `OMR_TEST_MODE=1` |
| POST | `/test/seed-scored-sheet` | Test-only seed | Gated by `OMR_TEST_MODE=1` |

**No mock/stub endpoints** in production paths except test helpers above.

---

## 5. OMR processing engine specifics

### Alignment / deskew

**Implemented.** `backend/app/omr/align.py`:

- Vendored OMRChecker **CropOnMarkers**: quadrant `cv2.matchTemplate` on bullseye markers, four-point perspective warp, resize to `pageDimensions`.
- Corner repair / bottom extrapolation when markers obscured (reference geometry from `blank_template.png`).
- Returns `WarpResult` with `marker_scores`, `quality`, `corners_repaired`.
- Optional grid refinement in `bubble_refine.py` (contour snap).

**Not used:** vendored `FeatureBasedAlignment.py` in app pipeline (only CropOnMarkers path).

### Roll number decode

**Implemented** in `backend/app/omr/roll_number.py`:

- Reads **6-digit bubble matrix** (QTYPE_INT columns); barcodes explicitly ignored (docstring).
- Per-column dynamic threshold; ambiguous → `?` and `ROLL_AMBIGUOUS`.
- Uses same fill measurement as MCQ (`fill_value_adaptive` + `dynamic_threshold`).

### Bubble fill density / threshold

**Dynamic, mostly hardcoded in code — not driven by `config.yaml` `omr.*` fields.**

| Mechanism | Location |
|-----------|----------|
| Fill metric | `255 - mean(gray box)` (`threshold.py`) |
| Per-sheet cutoff | `dynamic_threshold()` — widest gap in sorted fills |
| MCQ answered vs multi | `MIN_MARK_MARGIN`, `MIN_DOMINANCE_RATIO`, `HARD_MULTI_*` constants in `bubbles.py` |
| Roll digit pick | `MIN_PLAUSIBLE_FILL`, margin 18.0, ratio 1.18 in `roll_number.py` |

`config.yaml` defines `fill_threshold`, `dynamic_threshold`, `blank_threshold`, `multi_mark_threshold` but **no references in `backend/app/omr/`** — dead config relative to actual pipeline.

### Confidence scoring

**Partial / implicit only:**

- No persisted per-field confidence scores.
- `alignment_quality` computed in `pipeline.py` but **not written** to `sheet_results.counts_json` (only `aligned`, `roll_status`, counts).
- Verification triggered by **hard multi** (`is_hard_multi`) and **roll ambiguous**, not low single-mark confidence.
- Soft multi resolved automatically in pipeline (top bubble wins if not "hard multi").

---

## 6. Flow-by-flow status

### Primary flows

| # | Flow | Status | Evidence |
|---|------|--------|----------|
| 1 | Exam profile creation (questions, layout blocks, answer key, negative marking) | ⚠️ Partial | Programs/sessions/keys: ✅ `program_service.py`, OperatorDashboard. Layout blocks: ⚠️ API + calibrator exist; sessions always create with `path_layout_id: null` (`index.tsx`). Negative marking: ❌ not in `scoring.py`. Subject splits: ⚠️ API only (`programs.py`). |
| 2 | Roster import/management | ❌ Not implemented | No roster model, API, or UI anywhere in `backend/app` / `frontend/src`. |
| 3 | Scan ingestion into watched folder | ✅ Fully implemented | `dropzone.py`, `handler.py`, `ingestion.py`; SHA-256 dedupe in `ingested_files`. |
| 4 | Batch detection + assignment to exam | ⚠️ Partial | Assignment = operator starts ingestion for a **chosen session** (`DropzoneController.start(session_id)`). No auto-detect exam from sheet content. Debounced auto-flush → `batch_processor.start_batch`. |
| 5 | Sheet alignment, roll decode, response extraction | ✅ Fully implemented | `align.py`, `roll_number.py`, `bubbles.py`, `pipeline.py`, `batch_processor._process_one`. |
| 6 | Roll-number-vs-roster + fill-confidence check | ❌ Not implemented | No roster. No low-confidence queue beyond hard-multi / roll-ambiguous. Misaligned sheets stored with `aligned: false`, no verification item (`pipeline.py` lines 96–97, `batch_processor.py`). |
| 7 | Verification queue + hotkey override (L-key) | ✅ Fully implemented | Queue: `verification_service.py`, `VerificationQueue.tsx`. **L-key is real:** `pynput` global listener → WS broadcast (`hotkeys/listener.py`); UI must **manually** "Start global L-key". In-page A–D/Enter/S/F also work. |
| 8 | Results compilation and export | ✅ Fully implemented | Scoring: `scoring.py`. Export CSV/XLSX literal/binary: `export.py`, `ExportReport.tsx`. Program-level merge by roll in `build_program_table`. |

### Secondary flows

| # | Flow | Status | Evidence |
|---|------|--------|----------|
| 1 | Layout block (template) creation & reuse | ⚠️ Partial | Calibrator + `/templates` CRUD ✅. Session linkage ⚠️ API supports `path_layout_id` but UI never sets it. Default seed layout used via `template_service.resolve_session_template`. |
| 2 | Subject split definition | ⚠️ Partial | DB + REST ✅ (`SubjectSplit`, `programs.py`). No frontend. Used in scoring/export if rows exist. |
| 3 | Roster maintenance outside a live batch | ❌ Not implemented | No roster. |
| 4 | Report export (binary vs literal, CSV/XLSX) | ✅ Fully implemented | `export.py` modes `literal`/`binary`, formats `csv`/`xlsx`; UI in `ExportReport.tsx`. |
| 5 | Single-sheet audit drill-down | ❌ Not implemented | `/batches/{id}/sheets` exists; no UI to browse one sheet's per-question read/key/score. |

### Tertiary flows

| # | Flow | Status | Evidence |
|---|------|--------|----------|
| 1 | Roll number mismatch resolution | ⚠️ Partial | Ambiguous roll → verification queue + manual override ✅. **No roster mismatch** (unknown roll vs expected list). |
| 2 | Duplicate roll number resolution | ❌ Not implemented | Program export merges answers by `roll_no` silently (`export.py` `merged.setdefault(roll, {})`). No duplicate detection UI. |
| 3 | Batch reconciliation (expected vs scanned count) | ❌ Not implemented | No expected count field; no reconciliation API/UI. |
| 4 | Sheet exclusion & reprocessing | ❌ Not implemented | No exclude flag or re-run endpoint. Failed sheets recorded; duplicates skipped at ingest. |
| 5 | Answer key correction + rescoring | ⚠️ Partial | Key upsert + `answer_key_audit` ✅. Scores computed **on read** from current key (`score_session`) — no explicit "rescore job" or sheet invalidation. |
| 6 | Threshold calibration UI | ❌ Not implemented | Thresholds hardcoded in `threshold.py` / `bubbles.py`; config values unused. Calibrator adjusts geometry only. |
| 7 | Flag-for-review / second-pass queue | ⚠️ Partial | `resolve(..., action="flag")` sets status `flagged` ✅. No separate second-pass queue or UI filter for flagged items. |
| 8 | Backup & restore | ❌ Not implemented | `BACKUPS_DIR` created in `paths.py` only; no backup/restore code. |
| 9 | Audit trail / override logging | ⚠️ Partial | Answer-key changes: `answer_key_audit` ✅. Verification overrides: stored on `verification_queue.resolved_value` only — **no operator/timestamp audit table** for overrides. |

---

## 7. Known gaps, TODOs, and rough edges

### Config vs implementation

- `config.yaml` `omr.*` and `processing.max_workers` are **defined but unused** in app OMR/batch code (`config.py` only; batch uses single daemon thread per batch).

### Schema / model unused columns

- `path_layouts.roll_number_json`, `anchor_json` — columns exist, template storage uses `columns_json` only (`template_service.py`).

### Empty / swallow catch blocks (application code)

| File | Line(s) | Note |
|------|---------|------|
| `frontend/src/pages/OperatorDashboard/index.tsx` | 113–114 | Ingestion poll errors ignored |
| `frontend/src/context/PendingContext.tsx` | 20–22 | Pending fetch errors ignored |
| `frontend/src/pages/VerificationQueue.tsx` | 85–87, 89 | WS parse/error ignored |
| `backend/app/hotkeys/listener.py` | 90–91 | `pass` on listener stop |
| `backend/app/api/batches.py` | 84–85 | `pass` on WS close |
| `backend/app/watcher/dropzone.py` | 69–70 | PDF expand failure → `[]` silently |

### Test / seed mock data

- `backend/app/api/test_helpers.py` — synthetic batches/sheets/verification items when `OMR_TEST_MODE=1` (not production).

### Hardcoded UI defaults

- New session template family default `"150Q"`, sheet count `"20"` (`OperatorDashboard/index.tsx`).

### Vendored OMRChecker TODOs (not app layer)

Many TODO/FIXME in `backend/omr_engine/src/` (e.g. `core.py`, `evaluation.py`, `entry.py`) — legacy upstream code; app pipeline does not call `entry.py` CLI path for batch processing.

### Other rough edges

- **No project-level README** for operator setup (only `omr_engine/README.md`).
- **Batch WebSocket** (`/ws/batch/{id}`) has no frontend consumer.
- **`/ingestion/flush`** not exposed in UI (debounce handles flush automatically).
- **Delete session** UI message says keys removed; keys are program-level — delete session does not delete answer keys (`SessionTable.tsx` vs `program_service.delete_session`).
- **Scoring** is simple correct/wrong/blank/multi; no negative marks, no weighted questions.
- **Aligned failures** produce empty answers without operator queue entry.
- **opencv-python-headless** unpinned — reproducible CV behavior not locked in repo.

---

## 8. Output format

This document uses the requested section headers (1–8). Summary for gap-analysis consumers:

**Strong:** dropzone ingestion, OMR read pipeline (align + roll + MCQ), batch processing, verification queue with real global L-key, scoring, CSV/XLSX export, layout calibrator.

**Weak or missing:** roster entirely, negative marking, config-driven thresholds, batch/sheet admin UI, reconciliation, duplicate-roll handling, backup/restore, verification audit trail, roster/confidence gating, exam auto-assignment from scans, subject-split UI, path layout selection in run-exam flow.

**Schema:** SQLite + SQLAlchemy `create_all`; responses and overrides denormalized into JSON / verification_queue rather than classic normalized tables.
