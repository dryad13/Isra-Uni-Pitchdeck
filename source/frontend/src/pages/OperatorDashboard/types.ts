export type Program = { id: number; name: string; key_coverage_end: number | null };

export type SessionRow = {
  id: number;
  name: string;
  template_family: string;
  scan_template_family: string | null;
  session_order: number;
  sheet_question_count: number;
  global_q_start: number;
  global_q_end: number;
  key_complete: boolean;
  key_filled?: number;
  key_total?: number;
};

export type SubjectSplit = {
  id: number;
  subject_name: string;
  q_start: number;
  q_end: number;
};

export type ProgramDetail = {
  program: Program;
  sessions: SessionRow[];
  subjects?: SubjectSplit[];
};

export type Family = { family: string; max_questions: number };

/** Operator-facing answer sheet types (maps to backend template families). */
export const SHEET_TYPES = [
  { value: "150Q", label: "150 questions", maxQuestions: 150 },
  { value: "60Q", label: "60 questions", maxQuestions: 60 },
] as const;

export type SheetTypeValue = (typeof SHEET_TYPES)[number]["value"];

export type KeyStatus = {
  session_id: number;
  global_q_start: number;
  global_q_end: number;
  filled: number;
  total: number;
  ready: boolean;
  keys: { question_no: number; correct_option: string }[];
};

export type IngestionStatus = {
  watching: boolean;
  active_session_id: number | null;
  dropzone_path: string;
  pending_count: number;
  ingested_count: number;
  duplicate_count: number;
  skipped_count?: number;
  last_skip?: string | null;
  last_batch_id: number | null;
  expected_count?: number | null;
  last_error: string | null;
};

export type BatchSummary = {
  id: number;
  status: string;
  pending_verifications: number;
  progress_pct?: number;
  done_count?: number;
  total_files?: number;
  failed_count?: number;
  queued_count?: number;
  can_resume?: boolean;
  is_running?: boolean;
};

export type Layout = { id: number; name: string; template_family: string };

export type NewSessionForm = {
  name: string;
  template_family: SheetTypeValue;
  scan_template_family: SheetTypeValue | null;
  sheet_question_count: string;
  negative_marking_ratio: string;
};

export const OPTIONS = ["A", "B", "C", "D"];
export const MAX_SHEET_QUESTIONS = 150;

export function keyLozengeLabel(filled: number, total: number, ready: boolean) {
  return `${filled}/${total} answers · ${ready ? "ready" : "pending"}`;
}
