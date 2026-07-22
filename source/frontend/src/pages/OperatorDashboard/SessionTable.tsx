import { useState } from "react";
import Button from "../../components/Button";
import ConfirmDialog from "../../components/ConfirmDialog";
import Lozenge from "../../components/Lozenge";
import { keyLozengeLabel, type SessionRow } from "./types";

type Props = {
  sessions: SessionRow[];
  selectedSessionId: number | null;
  onSelect: (id: number) => void;
  onDelete: (id: number) => Promise<void>;
  deleting?: boolean;
};

export default function SessionTable({
  sessions,
  selectedSessionId,
  onSelect,
  onDelete,
  deleting,
}: Props) {
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const confirmSession = sessions.find((s) => s.id === confirmId);

  const handleDelete = async () => {
    if (confirmId == null) return;
    await onDelete(confirmId);
    setConfirmId(null);
  };

  return (
    <>
      <table className="data-table">
        <thead>
          <tr>
            <th aria-label="Select" />
            <th>#</th>
            <th>Session</th>
            <th>Questions</th>
            <th>Global range</th>
            <th>Answer key</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr
              key={s.id}
              className={s.id === selectedSessionId ? "selected" : undefined}
              aria-selected={s.id === selectedSessionId}
              onClick={() => onSelect(s.id)}
              style={{ cursor: "pointer" }}
            >
              <td onClick={(e) => e.stopPropagation()}>
                <input
                  type="radio"
                  className="session-radio"
                  name="session-select"
                  checked={s.id === selectedSessionId}
                  onChange={() => onSelect(s.id)}
                  aria-label={`Select ${s.name}`}
                />
              </td>
              <td>{s.session_order}</td>
              <td>{s.name}</td>
              <td>{s.sheet_question_count}</td>
              <td>
                Q{s.global_q_start}&ndash;Q{s.global_q_end}
              </td>
              <td>
                <Lozenge appearance={s.key_complete ? "success" : "warning"}>
                  {keyLozengeLabel(
                    s.key_filled ?? 0,
                    s.key_total ?? s.sheet_question_count,
                    s.key_complete,
                  )}
                </Lozenge>
              </td>
              <td>
                <Button
                  variant="danger-link"
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirmId(s.id);
                  }}
                >
                  delete
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <ConfirmDialog
        open={confirmId != null}
        title="Delete session?"
        message={
          confirmSession
            ? `"${confirmSession.name}" and its scan batches will be removed. Program answer keys are kept. This cannot be undone.`
            : ""
        }
        confirmLabel="Delete"
        danger
        busy={deleting}
        onConfirm={handleDelete}
        onCancel={() => setConfirmId(null)}
      />
    </>
  );
}
