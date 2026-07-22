import { useState } from "react";
import { Link } from "react-router-dom";
import Button from "../../components/Button";
import ConfirmDialog from "../../components/ConfirmDialog";
import Field from "../../components/Field";
import FileUpload from "../../components/FileUpload";
import Lozenge from "../../components/Lozenge";
import SectionMessage from "../../components/SectionMessage";
import type { BatchSummary, IngestionStatus } from "./types";

type Props = {
  keyReady: boolean;
  scanningThisSession: boolean;
  watching: boolean;
  ingestion: IngestionStatus | null;
  lastBatchSummary: BatchSummary | null;
  expectedCount: string;
  onExpectedCountChange: (v: string) => void;
  onStartScanning: () => Promise<void>;
  onStopScanning: () => Promise<void>;
  onUploadScan: (file: File) => Promise<void>;
  onResumeBatch?: (batchId: number) => Promise<void>;
  interruptedBatch?: BatchSummary | null;
  starting?: boolean;
  stopping?: boolean;
  uploading?: boolean;
};

export default function StepScanning({
  keyReady,
  scanningThisSession,
  watching,
  ingestion,
  lastBatchSummary,
  expectedCount,
  onExpectedCountChange,
  onStartScanning,
  onStopScanning,
  onUploadScan,
  onResumeBatch,
  interruptedBatch,
  starting,
  stopping,
  uploading,
}: Props) {
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const handleFile = (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;
    if (!scanningThisSession) {
      setPendingFile(file);
      return;
    }
    void onUploadScan(file);
  };

  const confirmStartAndUpload = async () => {
    if (!pendingFile) return;
    await onStartScanning();
    await onUploadScan(pendingFile);
    setPendingFile(null);
  };

  return (
    <div className="panel">
      <div className={`step ${scanningThisSession ? "step-active" : ""}`}>
        <span className="step-num">3</span>
        <div className="step-body">
          <div className="step-head">
            <h2>Process scanned sheets</h2>
            {watching && <Lozenge appearance="progress">watching</Lozenge>}
          </div>

          {!keyReady && (
            <p className="muted">Finish the answer key in step 2 before processing sheets.</p>
          )}

          {keyReady && (
            <div className="stack">
              {interruptedBatch?.can_resume && (
                <SectionMessage appearance="warning">
                  Batch #{interruptedBatch.id} interrupted — {interruptedBatch.done_count ?? 0}/
                  {interruptedBatch.total_files ?? "?"} sheets processed.
                  {onResumeBatch && (
                    <div style={{ marginTop: 8 }}>
                      <Button
                        variant="primary"
                        className="btn-touch"
                        onClick={() => void onResumeBatch(interruptedBatch.id)}
                      >
                        Resume batch
                      </Button>
                    </div>
                  )}
                </SectionMessage>
              )}

              <p className="muted">
                Click <strong>Start scan</strong>, then copy JPG/TIFF/PDF files into{" "}
                <code>{ingestion?.dropzone_path ?? "C:\\OMR_Dropzone"}</code> or upload below.
                Files already in that folder are picked up when scanning starts.
              </p>

              <div className="field-row">
                {!scanningThisSession && (
                  <Field label="Expected sheets" hint="Optional" htmlFor="expected-count">
                    <input
                      id="expected-count"
                      type="number"
                      min={1}
                      placeholder="e.g. 120"
                      value={expectedCount}
                      onChange={(e) => onExpectedCountChange(e.target.value)}
                    />
                  </Field>
                )}
              </div>

              <div className="row">
                {!scanningThisSession ? (
                  <Button
                    variant="primary"
                    className="btn-touch"
                    onClick={onStartScanning}
                    disabled={starting}
                  >
                    {starting ? "Starting…" : "Start scan"}
                  </Button>
                ) : (
                  <Button
                    variant="danger"
                    className="btn-touch"
                    onClick={onStopScanning}
                    disabled={stopping}
                  >
                    {stopping ? "Stopping…" : "Stop scan"}
                  </Button>
                )}
              </div>

              <Field label="Upload scan" hint="JPG, TIFF, or PDF" htmlFor="scan-file">
                <FileUpload
                  id="scan-file"
                  accept=".jpg,.jpeg,.tif,.tiff,.pdf,image/jpeg,image/tiff,application/pdf"
                  disabled={!keyReady}
                  busy={uploading}
                  onFile={handleFile}
                  hint="Drop a scan here or choose a file"
                />
              </Field>

              {watching && ingestion && (
                <div
                  className={`ingestion-card${ingestion.pending_count > 0 ? " ingestion-card-pulse" : ""}`}
                >
                  <div className="ingestion-stats">
                    <span className="ingestion-stat">
                      <strong>{ingestion.ingested_count}</strong> ingested
                    </span>
                    {ingestion.expected_count != null && ingestion.expected_count > 0 && (
                      <span className="ingestion-stat">
                        Scanned <strong>{ingestion.ingested_count}</strong> of{" "}
                        <strong>{ingestion.expected_count}</strong> expected
                      </span>
                    )}
                    {ingestion.duplicate_count > 0 && (
                      <span className="ingestion-stat">
                        <strong>{ingestion.duplicate_count}</strong> duplicate
                      </span>
                    )}
                    {ingestion.pending_count > 0 && (
                      <span className="ingestion-stat">
                        <strong>{ingestion.pending_count}</strong> pending
                      </span>
                    )}
                    {ingestion.last_batch_id != null && (
                      <span className="muted">Batch #{ingestion.last_batch_id}</span>
                    )}
                  </div>
                  {lastBatchSummary != null &&
                    lastBatchSummary.status === "needs_verification" &&
                    lastBatchSummary.pending_verifications > 0 && (
                      <div style={{ marginTop: 12 }}>
                        <Link to={`/verify?batch=${lastBatchSummary.id}`}>
                          <Button variant="primary" className="btn-touch">
                            Review batch #{lastBatchSummary.id} (
                            {lastBatchSummary.pending_verifications} pending)
                          </Button>
                        </Link>
                      </div>
                    )}
                </div>
              )}

              {ingestion?.last_skip && (
                <SectionMessage appearance="info">Skipped: {ingestion.last_skip}</SectionMessage>
              )}
              {ingestion?.last_error && (
                <SectionMessage appearance="error">{ingestion.last_error}</SectionMessage>
              )}
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={pendingFile != null}
        title="Start scanning first?"
        message={`Scanning is not active. Start processing for this session and upload "${pendingFile?.name}"?`}
        confirmLabel="Start and upload"
        onConfirm={confirmStartAndUpload}
        onCancel={() => setPendingFile(null)}
      />
    </div>
  );
}
