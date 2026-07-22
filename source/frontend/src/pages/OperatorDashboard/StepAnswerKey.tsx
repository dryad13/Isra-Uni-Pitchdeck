import { useState } from "react";
import Button from "../../components/Button";
import Field from "../../components/Field";
import FileUpload from "../../components/FileUpload";
import Lozenge from "../../components/Lozenge";
import Tabs from "../../components/Tabs";
import { OPTIONS, keyLozengeLabel, type KeyStatus, type SessionRow } from "./types";

type Tab = "sheet" | "file" | "manual";

type Props = {
  selectedSession: SessionRow | null;
  keyStatus: KeyStatus | null;
  keyDraft: Record<number, string>;
  onKeyDraftChange: (draft: Record<number, string>) => void;
  keyReady: boolean;
  keyFilled: number;
  keyTotal: number;
  onUploadSheet: (files: FileList | null) => Promise<void>;
  onUploadFile: (files: FileList | null) => Promise<void>;
  onSaveManual: () => Promise<void>;
  uploadingSheet?: boolean;
  uploadingFile?: boolean;
  savingManual?: boolean;
};

export default function StepAnswerKey({
  selectedSession,
  keyStatus,
  keyDraft,
  onKeyDraftChange,
  keyReady,
  keyFilled,
  keyTotal,
  onUploadSheet,
  onUploadFile,
  onSaveManual,
  uploadingSheet,
  uploadingFile,
  savingManual,
}: Props) {
  const [tab, setTab] = useState<Tab>("sheet");

  return (
    <div className="panel">
      <div className={`step ${keyReady ? "step-done" : selectedSession ? "step-active" : ""}`}>
        <span className="step-num">2</span>
        <div className="step-body">
          <div className="step-head">
            <h2>Load the answer key</h2>
            {keyStatus && (
              <Lozenge appearance={keyReady ? "success" : "warning"}>
                {keyLozengeLabel(keyFilled, keyTotal, keyReady)}
              </Lozenge>
            )}
          </div>

          {!selectedSession && (
            <p className="muted">Select a session in step 1 to load its answer key.</p>
          )}

          {selectedSession && keyStatus && (
            <>
              <Tabs
                variant="default"
                ariaLabel="Answer key source"
                items={[
                  { id: "sheet", label: "Upload sheet" },
                  { id: "file", label: "Upload file" },
                  { id: "manual", label: "Enter manually" },
                ]}
                activeId={tab}
                onChange={(id) => setTab(id as Tab)}
              />

              {tab === "sheet" && (
                <Field
                  label="Upload marked answer sheet"
                  hint="Scan or photo of a pre-filled template — bubbles are read automatically"
                  htmlFor="key-sheet-file"
                >
                  <FileUpload
                    id="key-sheet-file"
                    accept=".jpg,.jpeg,.png,.tif,.tiff,.pdf"
                    busy={uploadingSheet}
                    onFile={(files) => void onUploadSheet(files)}
                    hint="JPG, PNG, TIFF, or PDF"
                  />
                </Field>
              )}

              {tab === "file" && (
                <Field
                  label="Upload CSV or Excel"
                  hint="Columns: question_no, correct_option"
                  htmlFor="key-file"
                >
                  <FileUpload
                    id="key-file"
                    accept=".csv,.xlsx,.xls"
                    busy={uploadingFile}
                    onFile={(files) => void onUploadFile(files)}
                    hint="CSV or Excel spreadsheet"
                  />
                </Field>
              )}

              {tab === "manual" && (
                <>
                  <div className="key-table-wrap">
                    <table className="data-table key-table">
                      <thead>
                        <tr>
                          <th>Global Q</th>
                          <th>Sheet Q</th>
                          <th>Answer</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Array.from(
                          { length: keyStatus.global_q_end - keyStatus.global_q_start + 1 },
                          (_, i) => {
                            const globalQ = keyStatus.global_q_start + i;
                            const sheetQ = i + 1;
                            const value = keyDraft[globalQ] ?? "";
                            return (
                              <tr key={globalQ} className={value ? undefined : "key-row-empty"}>
                                <td>Q{globalQ}</td>
                                <td className="muted">s{sheetQ}</td>
                                <td>
                                  <select
                                    className="key-table-select"
                                    aria-label={`Answer for question ${globalQ}`}
                                    value={value}
                                    onChange={(e) =>
                                      onKeyDraftChange({
                                        ...keyDraft,
                                        [globalQ]: e.target.value,
                                      })
                                    }
                                  >
                                    <option value="">—</option>
                                    {OPTIONS.map((o) => (
                                      <option key={o} value={o}>
                                        {o}
                                      </option>
                                    ))}
                                  </select>
                                </td>
                              </tr>
                            );
                          },
                        )}
                      </tbody>
                    </table>
                  </div>
                  <Button onClick={onSaveManual} disabled={savingManual}>
                    {savingManual ? "Saving…" : "Save answers"}
                  </Button>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
