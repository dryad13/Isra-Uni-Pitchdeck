import { useState } from "react";
import Button from "../../components/Button";
import EmptyState from "../../components/EmptyState";
import Field from "../../components/Field";
import Spinner from "../../components/Spinner";
import SessionTable from "./SessionTable";
import {
  SHEET_TYPES,
  type NewSessionForm,
  type Program,
  type SessionRow,
  type SheetTypeValue,
} from "./types";

type Props = {
  programs: Program[];
  selectedProgramId: number | null;
  onSelectProgram: (id: number | null) => void;
  newProgramName: string;
  onNewProgramName: (v: string) => void;
  onCreateProgram: () => Promise<void>;
  creatingProgram?: boolean;
  sessions: SessionRow[];
  selectedSessionId: number | null;
  onSelectSession: (id: number) => void;
  onDeleteSession: (id: number) => Promise<void>;
  deletingSession?: boolean;
  newSession: NewSessionForm;
  onNewSession: (v: NewSessionForm) => void;
  suggestedStart: number;
  onCreateSession: () => Promise<void>;
  creatingSession?: boolean;
  loading?: boolean;
};

function clampQuestionCount(raw: string, max: number): string {
  const n = Number(raw);
  if (!Number.isFinite(n) || n < 1) return "1";
  return String(Math.min(max, Math.max(1, Math.floor(n))));
}

export default function StepExamSession({
  programs,
  selectedProgramId,
  onSelectProgram,
  newProgramName,
  onNewProgramName,
  onCreateProgram,
  creatingProgram,
  sessions,
  selectedSessionId,
  onSelectSession,
  onDeleteSession,
  deletingSession,
  newSession,
  onNewSession,
  suggestedStart,
  onCreateSession,
  creatingSession,
  loading,
}: Props) {
  const sheetMax = SHEET_TYPES.find((s) => s.value === newSession.template_family)?.maxQuestions ?? 150;
  const [scoringMode, setScoringMode] = useState<"standard" | "negative">("standard");

  const setStandardScoring = () => {
    setScoringMode("standard");
    onNewSession({ ...newSession, negative_marking_ratio: "0" });
  };

  const setNegativeScoring = () => {
    setScoringMode("negative");
    if (!newSession.negative_marking_ratio || newSession.negative_marking_ratio === "0") {
      onNewSession({ ...newSession, negative_marking_ratio: "0.25" });
    }
  };

  return (
    <div className="panel">
      <div className="step step-active">
        <span className="step-num">1</span>
        <div className="step-body">
          <div className="step-head">
            <h2>Choose exam and session</h2>
          </div>

          {loading && <Spinner label="Loading exams…" />}

          {!loading && programs.length === 0 && (
            <EmptyState
              title="No exams yet"
              description="Create your first exam program to get started."
            />
          )}

          <div className="field-row" style={{ marginBottom: 16 }}>
            <Field label="Exam program" htmlFor="program-select">
              <select
                id="program-select"
                value={selectedProgramId ?? ""}
                onChange={(e) =>
                  onSelectProgram(e.target.value ? Number(e.target.value) : null)
                }
              >
                <option value="">Select an exam</option>
                {programs.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="New exam name" htmlFor="new-program">
              <input
                id="new-program"
                value={newProgramName}
                placeholder="e.g. Weekly Test Batch A"
                onChange={(e) => onNewProgramName(e.target.value)}
              />
            </Field>
            <Button
              variant="default"
              onClick={onCreateProgram}
              disabled={!newProgramName || creatingProgram}
            >
              {creatingProgram ? "Creating…" : "Create exam"}
            </Button>
          </div>

          {selectedProgramId != null && (
            <>
              {sessions.length === 0 ? (
                <EmptyState
                  title="No sessions yet"
                  description="Add a session for each paper variant (e.g. Set A, Set B)."
                />
              ) : (
                <SessionTable
                  sessions={sessions}
                  selectedSessionId={selectedSessionId}
                  onSelect={onSelectSession}
                  onDelete={onDeleteSession}
                  deleting={deletingSession}
                />
              )}

              <div className="field-row" style={{ marginTop: 16 }}>
                <Field label="Session name" htmlFor="session-name">
                  <input
                    id="session-name"
                    value={newSession.name}
                    placeholder={`Next: Q${suggestedStart}+`}
                    onChange={(e) => onNewSession({ ...newSession, name: e.target.value })}
                  />
                </Field>
                <Field label="Answer sheet" htmlFor="session-sheet-type">
                  <select
                    id="session-sheet-type"
                    value={newSession.template_family}
                    onChange={(e) => {
                      const sheetType = e.target.value as SheetTypeValue;
                      const max = SHEET_TYPES.find((s) => s.value === sheetType)?.maxQuestions ?? 150;
                      onNewSession({
                        ...newSession,
                        template_family: sheetType,
                        scan_template_family: null,
                        sheet_question_count: clampQuestionCount(newSession.sheet_question_count, max),
                      });
                    }}
                  >
                    {SHEET_TYPES.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </Field>
                {newSession.template_family === "60Q" && (
                  <Field label="Scanner paper" htmlFor="scan-sheet-type">
                    <select
                      id="scan-sheet-type"
                      value={newSession.scan_template_family ?? "60Q"}
                      onChange={(e) => {
                        const v = e.target.value as SheetTypeValue;
                        onNewSession({
                          ...newSession,
                          scan_template_family:
                            v === newSession.template_family ? null : v,
                        });
                      }}
                    >
                      <option value="60Q">Same as answer sheet</option>
                      <option value="150Q">
                        150Q paper (first {newSession.sheet_question_count || "60"} questions)
                      </option>
                    </select>
                  </Field>
                )}
                <Field label="Questions on this sheet" htmlFor="session-q">
                  <input
                    id="session-q"
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    value={newSession.sheet_question_count}
                    onChange={(e) => {
                      const v = e.target.value;
                      if (v === "" || /^\d+$/.test(v)) {
                        onNewSession({ ...newSession, sheet_question_count: v });
                      }
                    }}
                    onBlur={() => {
                      onNewSession({
                        ...newSession,
                        sheet_question_count: clampQuestionCount(
                          newSession.sheet_question_count,
                          sheetMax,
                        ),
                      });
                    }}
                  />
                </Field>
                <Button
                  onClick={onCreateSession}
                  disabled={
                    !newSession.name ||
                    !newSession.sheet_question_count ||
                    creatingSession
                  }
                >
                  {creatingSession ? "Adding…" : "Add session"}
                </Button>
              </div>

              <div className="field-row scoring-options" style={{ marginTop: 12 }}>
                <div className="field">
                  <span className="field-label">Scoring</span>
                  <div className="radio-group">
                    <label className="radio-option">
                      <input
                        type="radio"
                        name="session-scoring"
                        checked={scoringMode === "standard"}
                        onChange={setStandardScoring}
                      />
                      Standard
                    </label>
                    <label className="radio-option">
                      <input
                        type="radio"
                        name="session-scoring"
                        checked={scoringMode === "negative"}
                        onChange={setNegativeScoring}
                      />
                      Negative marking
                    </label>
                  </div>
                </div>
                {scoringMode === "negative" && (
                  <Field label="Negative marking ratio" htmlFor="session-neg">
                    <input
                      id="session-neg"
                      type="number"
                      min={0}
                      step={0.25}
                      value={newSession.negative_marking_ratio}
                      onChange={(e) =>
                        onNewSession({ ...newSession, negative_marking_ratio: e.target.value })
                      }
                    />
                  </Field>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
