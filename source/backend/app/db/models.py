from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExamProgram(Base):
    __tablename__ = "exam_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    planned_max_questions: Mapped[int | None] = mapped_column(Integer)
    key_coverage_end: Mapped[int | None] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    roster_sync_mode: Mapped[str] = mapped_column(String(16), default="auto", nullable=False)

    sessions: Mapped[list["ExamSession"]] = relationship(back_populates="program")
    answer_keys: Mapped[list["AnswerKey"]] = relationship(back_populates="program")
    subject_splits: Mapped[list["SubjectSplit"]] = relationship(
        back_populates="program",
        foreign_keys="SubjectSplit.program_id",
    )
    students: Mapped[list["Student"]] = relationship(back_populates="program")


class PathLayout(Base):
    __tablename__ = "path_layouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_family: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    columns_json: Mapped[str | None] = mapped_column(Text)
    roll_number_json: Mapped[str | None] = mapped_column(Text)
    anchor_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    sessions: Mapped[list["ExamSession"]] = relationship(back_populates="path_layout")


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("exam_programs.id"), nullable=False)
    template_family: Mapped[str] = mapped_column(String(16), nullable=False)
    scan_template_family: Mapped[str | None] = mapped_column(String(16), nullable=True)
    session_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path_layout_id: Mapped[int | None] = mapped_column(ForeignKey("path_layouts.id"))
    sheet_question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    global_q_start: Mapped[int] = mapped_column(Integer, nullable=False)
    global_q_end: Mapped[int] = mapped_column(Integer, nullable=False)
    key_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exam_date: Mapped[date | None] = mapped_column(Date)
    batch_name: Mapped[str | None] = mapped_column(String(255))
    export_mode: Mapped[str] = mapped_column(String(32), default="literal")
    negative_marking_ratio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    program: Mapped["ExamProgram"] = relationship(back_populates="sessions")
    path_layout: Mapped["PathLayout | None"] = relationship(back_populates="sessions")
    scan_batches: Mapped[list["ScanBatch"]] = relationship(back_populates="session")
    subject_splits: Mapped[list["SubjectSplit"]] = relationship(
        back_populates="session",
        foreign_keys="SubjectSplit.session_id",
    )


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("program_id", "roll_no", name="uq_student_program_roll"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("exam_programs.id"), nullable=False)
    roll_no: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    class_section: Mapped[str | None] = mapped_column(String(128))
    batch_label: Mapped[str | None] = mapped_column(String(128))

    program: Mapped["ExamProgram"] = relationship(back_populates="students")


class AnswerKey(Base):
    __tablename__ = "answer_keys"
    __table_args__ = (
        UniqueConstraint("program_id", "question_no", name="uq_answer_key_program_question"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("exam_programs.id"), nullable=False)
    question_no: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_option: Mapped[str] = mapped_column(String(8), nullable=False)
    added_via_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("exam_sessions.id")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    program: Mapped["ExamProgram"] = relationship(back_populates="answer_keys")


class AnswerKeyAudit(Base):
    __tablename__ = "answer_key_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("exam_programs.id"), nullable=False)
    question_no: Mapped[int] = mapped_column(Integer, nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(8))
    new_value: Mapped[str | None] = mapped_column(String(8))
    changed_by: Mapped[str | None] = mapped_column(String(128))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class SubjectSplit(Base):
    __tablename__ = "subject_splits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[int | None] = mapped_column(ForeignKey("exam_programs.id"))
    session_id: Mapped[int | None] = mapped_column(ForeignKey("exam_sessions.id"))
    subject_name: Mapped[str] = mapped_column(String(255), nullable=False)
    q_start: Mapped[int] = mapped_column(Integer, nullable=False)
    q_end: Mapped[int] = mapped_column(Integer, nullable=False)

    program: Mapped["ExamProgram | None"] = relationship(
        back_populates="subject_splits",
        foreign_keys=[program_id],
    )
    session: Mapped["ExamSession | None"] = relationship(
        back_populates="subject_splits",
        foreign_keys=[session_id],
    )


class ScanBatch(Base):
    __tablename__ = "scan_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("exam_sessions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    expected_count: Mapped[int | None] = mapped_column(Integer)
    file_manifest_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    session: Mapped["ExamSession"] = relationship(back_populates="scan_batches")
    sheet_results: Mapped[list["SheetResult"]] = relationship(back_populates="batch")
    batch_files: Mapped[list["BatchFile"]] = relationship(back_populates="batch")


class BatchFile(Base):
    __tablename__ = "batch_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("scan_batches.id"), nullable=False)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    sheet_result_id: Mapped[int | None] = mapped_column(ForeignKey("sheet_results.id"))
    error_message: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    batch: Mapped["ScanBatch"] = relationship(back_populates="batch_files")


class IngestionState(Base):
    __tablename__ = "ingestion_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active_session_id: Mapped[int | None] = mapped_column(ForeignKey("exam_sessions.id"))
    expected_count: Mapped[int | None] = mapped_column(Integer)
    watching: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class SheetResult(Base):
    __tablename__ = "sheet_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("scan_batches.id"), nullable=False)
    roll_no: Mapped[str | None] = mapped_column(String(32))
    answers_json: Mapped[str | None] = mapped_column(Text)
    counts_json: Mapped[str | None] = mapped_column(Text)

    batch: Mapped["ScanBatch"] = relationship(back_populates="sheet_results")
    verification_items: Mapped[list["VerificationQueue"]] = relationship(
        back_populates="sheet"
    )


class VerificationQueue(Base):
    __tablename__ = "verification_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sheet_id: Mapped[int] = mapped_column(ForeignKey("sheet_results.id"), nullable=False)
    global_question_no: Mapped[int] = mapped_column(Integer, nullable=False)
    anomaly_type: Mapped[str] = mapped_column(String(32), nullable=False)
    crop_path: Mapped[str | None] = mapped_column(String(512))
    detected_values: Mapped[str | None] = mapped_column(Text)
    resolved_value: Mapped[str | None] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    resolved_by: Mapped[str | None] = mapped_column(String(128))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    sheet: Mapped["SheetResult"] = relationship(back_populates="verification_items")


class IngestedFile(Base):
    __tablename__ = "ingested_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("exam_sessions.id"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
