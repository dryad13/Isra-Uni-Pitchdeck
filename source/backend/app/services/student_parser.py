"""Student roster file parser (CSV / Excel)."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from app.services.answer_key_parser import _rows_from_csv, _rows_from_xlsx


class StudentParseError(ValueError):
    """Raised when a roster file cannot be parsed."""


_ROLL_ALIASES = {"roll", "roll_no", "rollno", "roll_number", "id", "student_id"}
_NAME_ALIASES = {"name", "student_name", "student", "full_name"}
_CLASS_ALIASES = {"class", "class_section", "section", "class_name"}
_BATCH_ALIASES = {"batch", "batch_label", "batch_name", "group"}


def _norm(s: str) -> str:
    return s.strip().lower().replace(" ", "_")


def _find_columns(header: list[str]) -> tuple[int | None, int | None, int | None, int | None]:
    roll_i = name_i = class_i = batch_i = None
    for idx, cell in enumerate(header):
        key = _norm(cell)
        if key in _ROLL_ALIASES and roll_i is None:
            roll_i = idx
        elif key in _NAME_ALIASES and name_i is None:
            name_i = idx
        elif key in _CLASS_ALIASES and class_i is None:
            class_i = idx
        elif key in _BATCH_ALIASES and batch_i is None:
            batch_i = idx
    return roll_i, name_i, class_i, batch_i


def parse_students(data: bytes, filename: str) -> list[tuple[str, str, str | None, str | None]]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        rows = _rows_from_csv(data)
    elif suffix in {".xlsx", ".xls"}:
        rows = _rows_from_xlsx(data)
    else:
        raise StudentParseError("Unsupported file type (use CSV or Excel).")

    if not rows:
        raise StudentParseError("File is empty.")

    roll_i, name_i, class_i, batch_i = _find_columns(rows[0])
    data_rows = rows[1:] if roll_i is not None and name_i is not None else rows

    if roll_i is None or name_i is None:
        if len(rows[0]) >= 2 and all(not _norm(c) for c in rows[0][:2]):
            roll_i, name_i = 0, 1
            class_i = 2 if len(rows[0]) > 2 else None
            batch_i = 3 if len(rows[0]) > 3 else None
            data_rows = rows
        elif len(rows[0]) >= 2:
            roll_i, name_i = 0, 1
            class_i = 2 if len(rows[0]) > 2 else None
            batch_i = 3 if len(rows[0]) > 3 else None
        else:
            raise StudentParseError(
                "Could not find roll_no and name columns. Expected headers like "
                "roll_no, name."
            )

    entries: list[tuple[str, str, str | None, str | None]] = []
    seen: set[str] = set()
    for line_no, row in enumerate(data_rows, start=1):
        if not any(cell.strip() for cell in row):
            continue
        try:
            roll = row[roll_i].strip()
            name = row[name_i].strip()
        except IndexError as exc:
            raise StudentParseError(f"Row {line_no}: not enough columns.") from exc
        if not roll or not name:
            continue
        if roll in seen:
            raise StudentParseError(f"Row {line_no}: duplicate roll {roll!r} in file.")
        seen.add(roll)
        class_section = row[class_i].strip() if class_i is not None and class_i < len(row) else None
        batch_label = row[batch_i].strip() if batch_i is not None and batch_i < len(row) else None
        entries.append(
            (
                roll,
                name,
                class_section or None,
                batch_label or None,
            )
        )

    if not entries:
        raise StudentParseError("No student rows found.")
    return entries
