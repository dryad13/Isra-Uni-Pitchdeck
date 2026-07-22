import Field from "./Field";
import {
  useExamScope,
  type ExamScopeValue,
  type ScopeLevel,
} from "../hooks/useExamScope";

type Props = {
  levels: ScopeLevel;
  value?: ExamScopeValue;
  onChange?: (value: ExamScopeValue) => void;
  syncUrl?: boolean;
  disabled?: boolean;
  className?: string;
};

export default function ExamScopePicker({
  levels,
  value: controlledValue,
  onChange,
  syncUrl = false,
  disabled = false,
  className = "",
}: Props) {
  const scope = useExamScope({ levels, syncUrl: syncUrl && !controlledValue });

  const programId = controlledValue?.programId ?? scope.programId;
  const sessionId = controlledValue?.sessionId ?? scope.sessionId;
  const batchId = controlledValue?.batchId ?? scope.batchId;

  const emit = (patch: Partial<ExamScopeValue>) => {
    if (onChange) {
      const next: ExamScopeValue = {
        programId: patch.programId !== undefined ? patch.programId : programId,
        sessionId: patch.sessionId !== undefined ? patch.sessionId : sessionId,
        batchId: patch.batchId !== undefined ? patch.batchId : batchId,
      };
      if (patch.programId !== undefined && patch.programId !== programId) {
        next.sessionId = null;
        next.batchId = null;
      }
      if (patch.sessionId !== undefined && patch.sessionId !== sessionId) {
        next.batchId = null;
      }
      onChange(next);
    } else {
      scope.setScope(patch);
    }
  };

  const showSession =
    levels === "program+session" || levels === "program+session+batch";
  const showBatch = levels === "program+session+batch";

  return (
    <div className={`field-row exam-scope-picker ${className}`.trim()}>
      <Field label="Exam program" htmlFor="scope-program">
        <select
          id="scope-program"
          value={programId ?? ""}
          disabled={disabled || scope.loading}
          onChange={(e) =>
            emit({
              programId: e.target.value ? Number(e.target.value) : null,
            })
          }
        >
          <option value="">Select exam…</option>
          {scope.programs.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </Field>

      {showSession && (
        <Field label="Session" htmlFor="scope-session">
          <select
            id="scope-session"
            value={sessionId ?? ""}
            disabled={disabled || programId == null}
            onChange={(e) =>
              emit({
                sessionId: e.target.value ? Number(e.target.value) : null,
              })
            }
          >
            <option value="">Select session…</option>
            {scope.sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </Field>
      )}

      {showBatch && (
        <Field label="Batch" htmlFor="scope-batch">
          <select
            id="scope-batch"
            value={batchId ?? ""}
            disabled={disabled || sessionId == null}
            onChange={(e) =>
              emit({
                batchId: e.target.value ? Number(e.target.value) : null,
              })
            }
          >
            <option value="">Select batch…</option>
            {scope.batches.map((b) => (
              <option key={b.id} value={b.id}>
                Batch #{b.id} ({b.status})
              </option>
            ))}
          </select>
        </Field>
      )}
    </div>
  );
}

export { useExamScope };
