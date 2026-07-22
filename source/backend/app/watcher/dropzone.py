"""M07 — Dropzone file watcher.

Watches the configured dropzone for new scans (Canon DR-M140 output), waits for
each file to be fully written (size-stable, no `.omr_lock` sibling), de-dupes by
SHA-256, records it, and buffers it for the active session. After a quiet period
the buffer auto-flushes into a processing batch (M08). PDFs are expanded to pages.

The file-handling core is decoupled from watchdog so it can be unit-tested by
calling `handle_file()` directly.
"""

from __future__ import annotations

import hashlib
import threading
import time
from datetime import datetime
from pathlib import Path

from app.config import get_config
from app.paths import PDF_PAGES_DIR
from app.db.models import IngestedFile
from app.db.session import SessionLocal
from app.services import batch_processor

PAGES_DIR = PDF_PAGES_DIR
_DEBOUNCE_SECONDS = 3.0


def compute_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def wait_until_stable(path: Path, lock_suffix: str, timeout: float = 30.0) -> bool:
    """Return True once the file is size-stable and its lock file is gone."""
    lock = path.with_name(path.name + lock_suffix)
    deadline = time.time() + timeout
    last_size = -1
    while time.time() < deadline:
        if lock.exists():
            time.sleep(0.5)
            continue
        try:
            size = path.stat().st_size
        except OSError:
            return False
        if size == last_size and size > 0:
            return True
        last_size = size
        time.sleep(0.5)
    return False


def expand_to_pages(path: Path) -> list[str]:
    """Images pass through; PDFs are converted to per-page PNGs."""
    if path.suffix.lower() != ".pdf":
        return [str(path)]
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return []
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        pages = convert_from_path(str(path))
    except Exception:
        return []
    out = []
    for i, page in enumerate(pages, start=1):
        out_path = PAGES_DIR / f"{path.stem}_p{i}.png"
        page.save(out_path, "PNG")
        out.append(str(out_path))
    return out


class DropzoneController:
    """Singleton-ish controller for the active dropzone watch session."""

    def __init__(self) -> None:
        self._observer = None
        self._active_session_id: int | None = None
        self._pending: list[str] = []
        self._lock = threading.Lock()
        self._debounce_timer: threading.Timer | None = None
        self._processing: set[str] = set()
        self.last_error: str | None = None
        self.last_batch_id: int | None = None
        self.expected_count: int | None = None
        self.ingested_count = 0
        self.duplicate_count = 0
        self.skipped_count = 0
        self.last_skip: str | None = None

    # --- lifecycle ---
    def start(self, session_id: int, expected_count: int | None = None) -> dict:
        cfg = get_config()
        dropzone = Path(cfg.dropzone.path)
        dropzone.mkdir(parents=True, exist_ok=True)
        self.stop()
        self._active_session_id = session_id
        self.expected_count = expected_count
        self.last_error = None
        self.last_skip = None
        self.ingested_count = 0
        self.duplicate_count = 0
        self.skipped_count = 0

        from watchdog.observers import Observer

        from app.watcher.handler import DropzoneEventHandler

        handler = DropzoneEventHandler(self)
        observer = Observer()
        observer.schedule(handler, str(dropzone), recursive=False)
        observer.start()
        self._observer = observer
        self._scan_existing_files(dropzone, cfg.dropzone.accepted_extensions)
        return self.status()

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
        if self._debounce_timer is not None:
            self._debounce_timer.cancel()
            self._debounce_timer = None

    # --- file handling (testable core) ---
    def ingest_path(self, path_str: str) -> None:
        """Queue a file for handling on a background thread."""
        threading.Thread(
            target=self.handle_file, args=(path_str,), daemon=True
        ).start()

    def _scan_existing_files(self, dropzone: Path, accepted: list[str]) -> None:
        """Pick up scans already sitting in the folder before the watcher started."""
        for path in sorted(dropzone.iterdir()):
            if path.is_file() and path.suffix.lower() in accepted:
                self.ingest_path(str(path))

    def handle_file(self, path_str: str) -> dict:
        cfg = get_config()
        path = Path(path_str)
        key = str(path.resolve())
        if key in self._processing:
            return {"skipped": "already_processing"}
        self._processing.add(key)
        try:
            return self._handle_file_inner(path, cfg)
        finally:
            self._processing.discard(key)

    def _handle_file_inner(self, path: Path, cfg) -> dict:
        suffix = path.suffix.lower()
        if cfg.dropzone.lock_suffix in path.name:
            self._note_skip("lock file ignored")
            return {"skipped": "lock_file"}
        if suffix not in cfg.dropzone.accepted_extensions:
            self._note_skip(f"unsupported type {suffix}")
            return {"skipped": "unsupported_extension"}
        if not path.exists():
            self._note_skip("file missing")
            return {"skipped": "missing"}
        if not wait_until_stable(path, cfg.dropzone.lock_suffix):
            self._note_skip("file not stable yet")
            return {"skipped": "not_stable"}

        pages = expand_to_pages(path)
        if not pages:
            self._note_skip(f"could not read pages from {path.name}")
            return {"skipped": "no_pages"}

        file_hash = compute_hash(path)
        db = SessionLocal()
        try:
            existing = (
                db.query(IngestedFile)
                .filter(
                    IngestedFile.file_hash == file_hash,
                    IngestedFile.processed_at.isnot(None),
                )
                .first()
            )
            if existing is not None:
                self.duplicate_count += 1
                self._note_skip(f"duplicate scan ({path.name})")
                return {"skipped": "duplicate", "hash": file_hash}
            record = IngestedFile(
                file_hash=file_hash,
                filename=path.name,
                session_id=self._active_session_id,
                processed_at=None,
            )
            db.add(record)
            db.commit()
        finally:
            db.close()

        with self._lock:
            self._pending.extend(pages)
            self.ingested_count += 1
        self.last_skip = None
        self._arm_debounce()
        return {"ingested": True, "pages": len(pages), "hash": file_hash}

    def _note_skip(self, reason: str) -> None:
        self.skipped_count += 1
        self.last_skip = reason

    def _arm_debounce(self) -> None:
        if self._debounce_timer is not None:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(_DEBOUNCE_SECONDS, self.flush)
        self._debounce_timer.daemon = True
        self._debounce_timer.start()

    def flush(self) -> dict:
        with self._lock:
            if not self._pending or self._active_session_id is None:
                return {"flushed": 0}
            files = list(self._pending)
            self._pending.clear()
        try:
            batch_id = batch_processor.start_batch(
                self._active_session_id, files, expected_count=self.expected_count
            )
            self.last_batch_id = batch_id
            self.last_error = None
            return {"flushed": len(files), "batch_id": batch_id}
        except batch_processor.BatchError as exc:
            self.last_error = str(exc)
            # Re-buffer so a later flush (after key completion) can retry.
            with self._lock:
                self._pending = files + self._pending
            return {"flushed": 0, "error": str(exc)}

    def status(self) -> dict:
        cfg = get_config()
        return {
            "watching": self._observer is not None,
            "active_session_id": self._active_session_id,
            "dropzone_path": cfg.dropzone.path,
            "pending_count": len(self._pending),
            "ingested_count": self.ingested_count,
            "duplicate_count": self.duplicate_count,
            "skipped_count": self.skipped_count,
            "last_skip": self.last_skip,
            "last_batch_id": self.last_batch_id,
            "expected_count": self.expected_count,
            "last_error": self.last_error,
        }


controller = DropzoneController()
