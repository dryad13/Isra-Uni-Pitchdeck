"""M08 — Batch Processor.

Runs an OMR batch in a background thread: reads each sheet via the M09 pipeline,
persists `SheetResult` rows, and enqueues `VerificationQueue` items for anomalies.
Progress is tracked on the `ScanBatch` row (polled by the API / WebSocket).

Guardrail (FR-1.3): a session cannot be scanned until its master-key slice is
complete.
"""

from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from app.config import get_config
from app.paths import CROPS_DIR
from app.db.models import BatchFile, ExamSession, IngestedFile, ScanBatch, SheetResult, VerificationQueue
from app.db.session import SessionLocal
from app.omr import roll_number as roll_reader
from app.omr.pipeline import SheetReader
from app.services import answer_key_service, batch_recovery, batch_worker, program_service, student_service, template_service

ROSTER_SYNC_AUTO = program_service.ROSTER_SYNC_AUTO

CROP_DIR = CROPS_DIR

ANOMALY_ROLL_UNMATCHED = "roll_unmatched"
ANOMALY_ROLL_DUPLICATE = "roll_duplicate"

_running: set[int] = set()
_lock = threading.Lock()


class BatchError(ValueError):
    """Raised when a batch cannot be started."""


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _insert_batch_files(db, batch_id: int, file_paths: list[str]) -> None:
    for idx, path in enumerate(file_paths):
        resolved = str(Path(path).resolve())
        fh = None
        try:
            fh = _file_hash(resolved)
        except OSError:
            fh = None
        db.add(
            BatchFile(
                batch_id=batch_id,
                source_path=resolved,
                file_hash=fh,
                sort_order=idx,
                status="queued",
                updated_at=datetime.utcnow(),
            )
        )
    db.commit()


def _queued_files(db, batch_id: int) -> list[BatchFile]:
    return (
        db.query(BatchFile)
        .filter(BatchFile.batch_id == batch_id, BatchFile.status == "queued")
        .order_by(BatchFile.sort_order)
        .all()
    )


def _mark_processing(db, batch_file: BatchFile) -> None:
    batch_file.status = "processing"
    batch_file.updated_at = datetime.utcnow()
    db.commit()


def _mark_done(db, batch_file: BatchFile, sheet_result_id: int) -> None:
    batch_file.status = "done"
    batch_file.sheet_result_id = sheet_result_id
    batch_file.error_message = None
    batch_file.updated_at = datetime.utcnow()
    if batch_file.file_hash:
        ingested = (
            db.query(IngestedFile)
            .filter(IngestedFile.file_hash == batch_file.file_hash)
            .first()
        )
        if ingested is not None and ingested.processed_at is None:
            ingested.processed_at = datetime.utcnow()
    db.commit()


def _mark_failed(db, batch_file: BatchFile, message: str, sheet_result_id: int | None) -> None:
    batch_file.status = "failed"
    batch_file.error_message = message[:2000]
    batch_file.sheet_result_id = sheet_result_id
    batch_file.updated_at = datetime.utcnow()
    db.commit()


def start_batch(
    session_id: int,
    file_paths: list[str],
    expected_count: int | None = None,
) -> int:
    """Validate, create a ScanBatch, and launch background processing."""
    db = SessionLocal()
    try:
        session = db.get(ExamSession, session_id)
        if session is None:
            raise BatchError(f"Session {session_id} not found.")
        status = answer_key_service.session_slice_status(db, session_id)
        if not status["ready"]:
            raise BatchError(
                f"Answer key incomplete for this session "
                f"(missing {len(status['missing'])} questions). Complete the key first."
            )
        if not file_paths:
            raise BatchError("No files to process.")

        now = datetime.utcnow()
        batch = ScanBatch(
            session_id=session_id,
            status="running",
            progress_pct=0.0,
            started_at=now,
            updated_at=now,
            expected_count=expected_count,
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        batch_id = batch.id
        _insert_batch_files(db, batch_id, file_paths)
    finally:
        db.close()

    _launch_batch_thread(batch_id, session_id)
    return batch_id


def resume_batch(batch_id: int) -> int:
    """Resume an interrupted batch from persisted queue rows."""
    db = SessionLocal()
    try:
        batch = db.get(ScanBatch, batch_id)
        if batch is None:
            raise BatchError(f"Batch {batch_id} not found.")
        with _lock:
            if batch_id in _running:
                raise BatchError(f"Batch {batch_id} is already running.")
        if not batch_recovery.can_resume_batch(db, batch, batch_id in _running):
            raise BatchError(f"Batch {batch_id} cannot be resumed.")
        now = datetime.utcnow()
        db.query(BatchFile).filter(
            BatchFile.batch_id == batch_id,
            BatchFile.status == "processing",
        ).update({"status": "queued", "updated_at": now}, synchronize_session=False)
        batch.status = "resuming"
        batch.file_manifest_version = (batch.file_manifest_version or 1) + 1
        batch.updated_at = now
        db.commit()
        session_id = batch.session_id
    finally:
        db.close()

    _launch_batch_thread(batch_id, session_id)
    return batch_id


def cancel_batch(batch_id: int) -> dict:
    """Cancel remaining queued files; finalize partial results."""
    db = SessionLocal()
    try:
        batch = db.get(ScanBatch, batch_id)
        if batch is None:
            raise BatchError(f"Batch {batch_id} not found.")
        with _lock:
            if batch_id in _running:
                raise BatchError("Cannot cancel a batch while it is running.")
        now = datetime.utcnow()
        db.query(BatchFile).filter(
            BatchFile.batch_id == batch_id,
            BatchFile.status.in_(["queued", "processing"]),
        ).update({"status": "cancelled", "updated_at": now}, synchronize_session=False)
        batch.status = "interrupted"
        batch.updated_at = now
        db.commit()
        _finalize(db, batch_id)
        return batch_summary(db, batch_id)
    finally:
        db.close()


def _launch_batch_thread(batch_id: int, session_id: int) -> None:
    thread = threading.Thread(
        target=_run_batch, args=(batch_id, session_id), daemon=True
    )
    with _lock:
        _running.add(batch_id)
    thread.start()


def _run_batch(batch_id: int, session_id: int) -> None:
    db = SessionLocal()
    try:
        session = db.get(ExamSession, session_id)
        try:
            template_dict, family = template_service.resolve_scan_template(db, session)
            from app.services.program_service import _agent_log

            _agent_log(
                "batch_processor.py:_run_batch",
                "scan template resolved",
                {
                    "session_id": session_id,
                    "key_template_family": session.template_family,
                    "scan_template_family": template_service.effective_scan_family(session),
                    "reader_family": family,
                    "sheet_question_count": session.sheet_question_count,
                },
                "A,B",
            )
        except template_service.TemplateError as exc:
            raise BatchError(str(exc)) from exc

        batch = db.get(ScanBatch, batch_id)
        if batch is not None:
            batch.status = "running"
            batch.updated_at = datetime.utcnow()
            db.commit()

        max_workers = max(1, get_config().processing.max_workers)
        queued = _queued_files(db, batch_id)
        total = (
            db.query(BatchFile).filter(BatchFile.batch_id == batch_id).count()
        )
        done_before = total - len(queued)

        if not queued:
            _finalize(db, batch_id)
            return

        if max_workers == 1:
            reader = SheetReader(template_dict, family)
            completed = done_before
            for batch_file in queued:
                _mark_processing(db, batch_file)
                try:
                    sheet_id = _process_one(
                        db, batch_id, session, reader, batch_file.source_path
                    )
                    _mark_done(db, batch_file, sheet_id)
                except Exception as exc:  # noqa: BLE001
                    sheet_id = _record_failed_sheet(
                        db, batch_id, batch_file.source_path, str(exc)
                    )
                    _mark_failed(db, batch_file, str(exc), sheet_id)
                completed += 1
                _update_progress(db, batch_id, completed, total)
        else:
            crop_dir = str(CROP_DIR)
            gq_start = session.global_q_start
            q_count = session.sheet_question_count
            completed = done_before
            with ProcessPoolExecutor(
                max_workers=max_workers,
                initializer=batch_worker.init_worker,
                initargs=(template_dict, family),
            ) as pool:
                future_map: dict = {}
                for batch_file in queued:
                    _mark_processing(db, batch_file)
                    prefix = f"b{batch_id}_{Path(batch_file.source_path).stem}"
                    future = pool.submit(
                        batch_worker.process_sheet_task,
                        batch_file.source_path,
                        gq_start,
                        q_count,
                        crop_dir,
                        prefix,
                    )
                    future_map[future] = batch_file

                for future in as_completed(future_map):
                    batch_file = future_map[future]
                    completed += 1
                    try:
                        result = future.result()
                        sheet_id = _persist_result(
                            db, batch_id, session, batch_file.source_path, result
                        )
                        _mark_done(db, batch_file, sheet_id)
                    except Exception as exc:  # noqa: BLE001
                        sheet_id = _record_failed_sheet(
                            db, batch_id, batch_file.source_path, str(exc)
                        )
                        _mark_failed(db, batch_file, str(exc), sheet_id)
                    _update_progress(db, batch_id, completed, total)

        _finalize(db, batch_id)
    except Exception as exc:  # noqa: BLE001
        batch = db.get(ScanBatch, batch_id)
        if batch is not None:
            batch.status = "failed"
            batch.updated_at = datetime.utcnow()
            db.commit()
        raise exc
    finally:
        db.close()
        with _lock:
            _running.discard(batch_id)


def _update_progress(db, batch_id: int, completed: int, total: int) -> None:
    batch = db.get(ScanBatch, batch_id)
    if batch is not None:
        batch.progress_pct = round(completed / total * 100.0, 1) if total else 100.0
        batch.updated_at = datetime.utcnow()
        db.commit()


def _enqueue_anomaly(db, sheet_id: int, anomaly_type: str, detected: str, global_q: int = 0) -> None:
    db.add(
        VerificationQueue(
            sheet_id=sheet_id,
            global_question_no=global_q,
            anomaly_type=anomaly_type,
            detected_values=detected,
            status="pending",
        )
    )


def _check_roll_roster_and_duplicates(
    db, sheet: SheetResult, session: ExamSession, batch_id: int
) -> None:
    roll_no = sheet.roll_no
    if not roll_no:
        return
    counts = json.loads(sheet.counts_json) if sheet.counts_json else {}
    if counts.get("roll_status") != roll_reader.ROLL_OK:
        return

    if student_service.find_student(db, session.program_id, roll_no) is None:
        program = session.program
        sync_mode = getattr(program, "roster_sync_mode", ROSTER_SYNC_AUTO) or ROSTER_SYNC_AUTO
        if sync_mode == ROSTER_SYNC_AUTO:
            student_service.upsert_roll_from_scan(db, session.program_id, roll_no)
        else:
            _enqueue_anomaly(db, sheet.id, ANOMALY_ROLL_UNMATCHED, roll_no)

    duplicate = (
        db.query(SheetResult)
        .filter(
            SheetResult.batch_id == batch_id,
            SheetResult.roll_no == roll_no,
            SheetResult.id != sheet.id,
        )
        .first()
    )
    if duplicate is not None:
        _enqueue_anomaly(
            db,
            sheet.id,
            ANOMALY_ROLL_DUPLICATE,
            f"{roll_no} (conflicts with sheet #{duplicate.id})",
        )


def _persist_result(
    db, batch_id: int, session: ExamSession, path: str, result: dict
) -> int:
    counts = result.get("counts", {})
    source_path = result.get("source_path") or str(Path(path).resolve())
    sheet = SheetResult(
        batch_id=batch_id,
        roll_no=result.get("roll_no"),
        answers_json=json.dumps(result.get("answers", {})),
        counts_json=json.dumps(
            {
                **counts,
                "aligned": result.get("aligned", False),
                "roll_status": result.get("roll_status"),
                "source_file": Path(path).name,
                "source_path": source_path,
                "alignment_quality": result.get("alignment_quality"),
                "anomaly_count": len(result.get("anomalies", [])),
                "excluded": False,
                "read_method_summary": result.get("read_method_summary"),
            }
        ),
    )
    db.add(sheet)
    db.flush()

    for anomaly in result.get("anomalies", []):
        db.add(
            VerificationQueue(
                sheet_id=sheet.id,
                global_question_no=anomaly["global_q"],
                anomaly_type=anomaly["type"],
                crop_path=anomaly.get("crop_path"),
                detected_values=anomaly.get("detected"),
                status="pending",
            )
        )

    if result.get("aligned"):
        _check_roll_roster_and_duplicates(db, sheet, session, batch_id)

    from app.services.program_service import _agent_log

    counts = result.get("counts") or {}
    _agent_log(
        "batch_processor.py:_persist_result",
        "sheet processed",
        {
            "session_id": session.id,
            "path": Path(path).name,
            "aligned": result.get("aligned"),
            "answered": counts.get("answered"),
            "blank": counts.get("blank"),
            "multi": counts.get("multi"),
            "key_template_family": session.template_family,
            "scan_template_family": template_service.effective_scan_family(session),
        },
        "A,C",
    )

    db.commit()
    return sheet.id


def _process_one(db, batch_id, session: ExamSession, reader: SheetReader, path: str) -> int:
    prefix = f"b{batch_id}_{Path(path).stem}"
    result = reader.process(
        path,
        global_q_start=session.global_q_start,
        sheet_question_count=session.sheet_question_count,
        crop_dir=CROP_DIR,
        crop_prefix=prefix,
    )
    return _persist_result(db, batch_id, session, path, result)


def _record_failed_sheet(db, batch_id, path: str, error: str) -> int:
    db.rollback()
    source_path = str(Path(path).resolve())
    sheet = SheetResult(
        batch_id=batch_id,
        roll_no=None,
        answers_json=json.dumps({}),
        counts_json=json.dumps(
            {
                "aligned": False,
                "error": error,
                "source_file": Path(path).name,
                "source_path": source_path,
                "excluded": False,
            }
        ),
    )
    db.add(sheet)
    db.flush()
    _enqueue_anomaly(db, sheet.id, "alignment_failed", f"processing error: {error}")
    db.commit()
    return sheet.id


def _finalize(db, batch_id: int) -> None:
    batch = db.get(ScanBatch, batch_id)
    counts = batch_recovery.batch_file_summary(db, batch_id)
    remaining = counts["queued"] + counts["processing"]
    pending = (
        db.query(VerificationQueue)
        .join(SheetResult, VerificationQueue.sheet_id == SheetResult.id)
        .filter(SheetResult.batch_id == batch_id, VerificationQueue.status == "pending")
        .count()
    )
    now = datetime.utcnow()
    if remaining > 0:
        batch.status = "interrupted"
        batch.progress_pct = round(
            (counts["done"] + counts["failed"]) / max(counts["total"], 1) * 100.0, 1
        )
    else:
        batch.status = "needs_verification" if pending else "completed"
        batch.progress_pct = 100.0
        batch.completed_at = now
    batch.updated_at = now
    db.commit()


def batch_summary(db, batch_id: int) -> dict:
    batch = db.get(ScanBatch, batch_id)
    if batch is None:
        raise BatchError(f"Batch {batch_id} not found.")
    sheets = db.query(SheetResult).filter(SheetResult.batch_id == batch_id).all()
    pending = (
        db.query(VerificationQueue)
        .join(SheetResult, VerificationQueue.sheet_id == SheetResult.id)
        .filter(SheetResult.batch_id == batch_id, VerificationQueue.status == "pending")
        .count()
    )
    file_counts = batch_recovery.batch_file_summary(db, batch_id)
    is_running = batch_id in _running
    return {
        "id": batch.id,
        "session_id": batch.session_id,
        "status": batch.status,
        "progress_pct": batch.progress_pct,
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
        "expected_count": batch.expected_count,
        "sheet_count": len(sheets),
        "pending_verifications": pending,
        "is_running": is_running,
        "queued_count": file_counts["queued"] + file_counts["processing"],
        "done_count": file_counts["done"],
        "failed_count": file_counts["failed"],
        "total_files": file_counts["total"],
        "can_resume": batch_recovery.can_resume_batch(db, batch, is_running),
    }


def list_batches(db, session_id: int, status: str | None = None) -> list[dict]:
    program_service.get_session(db, session_id)
    query = db.query(ScanBatch).filter(ScanBatch.session_id == session_id)
    if status:
        query = query.filter(ScanBatch.status == status)
    batches = query.order_by(ScanBatch.id.desc()).all()
    return [batch_summary(db, b.id) for b in batches]
