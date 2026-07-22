"""Student roster service — per-program roll number registry."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Student
from app.services import program_service


class StudentError(ValueError):
    """Raised for invalid student/roster operations."""


def list_students(
    db: Session, program_id: int, search: str | None = None,
    class_section: str | None = None,
    batch_label: str | None = None,
) -> list[Student]:
    program_service.get_program(db, program_id)
    query = db.query(Student).filter(Student.program_id == program_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (Student.roll_no.like(term))
            | (Student.name.like(term))
            | (Student.class_section.like(term))
        )
    if class_section and class_section.strip():
        query = query.filter(Student.class_section == class_section.strip())
    if batch_label and batch_label.strip():
        query = query.filter(Student.batch_label == batch_label.strip())
    return query.order_by(Student.roll_no.asc()).all()


def student_to_dict(student: Student) -> dict[str, Any]:
    return {
        "id": student.id,
        "program_id": student.program_id,
        "roll_no": student.roll_no,
        "name": student.name,
        "class_section": student.class_section,
        "batch_label": student.batch_label,
    }


def upsert_students(
    db: Session,
    program_id: int,
    entries: list[tuple[str, str, str | None, str | None]],
) -> dict[str, int]:
    program_service.get_program(db, program_id)
    created, updated = 0, 0
    for roll_no, name, class_section, batch_label in entries:
        roll = roll_no.strip()
        if not roll:
            raise StudentError("roll_no is required.")
        if not name.strip():
            raise StudentError(f"name is required for roll {roll!r}.")
        existing = (
            db.query(Student)
            .filter(Student.program_id == program_id, Student.roll_no == roll)
            .first()
        )
        if existing is None:
            db.add(
                Student(
                    program_id=program_id,
                    roll_no=roll,
                    name=name.strip(),
                    class_section=class_section,
                    batch_label=batch_label,
                )
            )
            created += 1
        else:
            existing.name = name.strip()
            existing.class_section = class_section
            existing.batch_label = batch_label
            updated += 1
    db.commit()
    return {"created": created, "updated": updated, "total": len(entries)}


def delete_student(db: Session, program_id: int, roll_no: str) -> None:
    program_service.get_program(db, program_id)
    row = (
        db.query(Student)
        .filter(Student.program_id == program_id, Student.roll_no == roll_no)
        .first()
    )
    if row is None:
        raise StudentError(f"Student roll {roll_no!r} not found.")
    db.delete(row)
    db.commit()


def find_student(db: Session, program_id: int, roll_no: str) -> Student | None:
    return (
        db.query(Student)
        .filter(Student.program_id == program_id, Student.roll_no == roll_no)
        .first()
    )


def upsert_roll_from_scan(
    db: Session,
    program_id: int,
    roll_no: str,
    name: str | None = None,
    class_section: str | None = None,
    batch_label: str | None = None,
    *,
    commit: bool = False,
) -> tuple[bool, Student]:
    """Create student from scan if missing. Returns (created, student). Does not overwrite existing."""
    roll = roll_no.strip()
    if not roll:
        raise StudentError("roll_no is required.")
    program_service.get_program(db, program_id)
    existing = find_student(db, program_id, roll)
    if existing is not None:
        return False, existing
    display_name = (name or "").strip() or roll
    student = Student(
        program_id=program_id,
        roll_no=roll,
        name=display_name,
        class_section=class_section,
        batch_label=batch_label,
    )
    db.add(student)
    if commit:
        db.commit()
        db.refresh(student)
    else:
        db.flush()
    return True, student
