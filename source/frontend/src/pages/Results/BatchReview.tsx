import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../../lib/api";
import Button from "../../components/Button";
import EmptyState from "../../components/EmptyState";
import ExamScopePicker from "../../components/ExamScopePicker";
import Lozenge from "../../components/Lozenge";
import OptionToggleGroup from "../../components/OptionToggleGroup";
import SectionMessage from "../../components/SectionMessage";
import Spinner from "../../components/Spinner";
import { useToast } from "../../components/Toast";
import { usePending } from "../../context/PendingContext";
import { useBusy } from "../../hooks/useBusy";
import type { ExamScopeValue } from "../../hooks/useExamScope";

type Flag = { type: string; label: string; global_q?: number };

type ReviewItem = {
  id: number;
  sheet_id: number;
  roll_no: string | null;
  batch_id: number | null;
  anomaly_type: string;
  global_question_no: number;
  sheet_question_no: number | null;
  detected_values: string | null;
  status: string;
  has_crop: boolean;
  has_source_image?: boolean;
  on_roster?: boolean | null;
};

type ReviewSheet = {
  sheet_id: number;
  roll_no: string | null;
  source_file: string | null;
  alignment_quality: number | null;
  status: string;
  pending_count: number;
  flags: Flag[];
  items: ReviewItem[];
};

type BatchReviewData = {
  batch_id: number;
  status: string;
  total_pending: number;
  sheets_needing_review: number;
  sheets: ReviewSheet[];
};

const MCQ_OPTIONS = ["A", "B", "C", "D", "BLANK"];

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

function isRollType(type: string) {
  return type === "roll_ambiguous" || type === "roll_unmatched";
}

function isSheetExcludeType(type: string) {
  return type === "alignment_failed" || type === "roll_duplicate";
}

function isAckType(type: string) {
  return type === "alignment_review";
}

function statusAppearance(status: string): "success" | "warning" | "danger" | "info" {
  if (status === "scored") return "success";
  if (status === "pending_verification") return "warning";
  if (status === "alignment_failed") return "danger";
  return "info";
}

type Props = {
  embedded?: boolean;
};

export default function BatchReview({ embedded = false }: Props) {
  const toast = useToast();
  const { refreshPending } = usePending();
  const [searchParams, setSearchParams] = useSearchParams();
  const initBusy = useBusy();
  const loadBusy = useBusy();
  const resolveBusy = useBusy();

  const [scope, setScope] = useState<ExamScopeValue>({
    programId: searchParams.get("program") ? Number(searchParams.get("program")) : null,
    sessionId: searchParams.get("session") ? Number(searchParams.get("session")) : null,
    batchId: searchParams.get("batch") ? Number(searchParams.get("batch")) : null,
  });
  const [review, setReview] = useState<BatchReviewData | null>(null);
  const [pendingOnly, setPendingOnly] = useState(true);
  const [selectedSheetId, setSelectedSheetId] = useState<number | null>(null);
  const [currentItemId, setCurrentItemId] = useState<number | null>(null);
  const [override, setOverride] = useState("");
  const [addToRoster, setAddToRoster] = useState(true);
  const [rosterName, setRosterName] = useState("");
  const [classSection, setClassSection] = useState("");
  const [batchLabel, setBatchLabel] = useState("");
  const [error, setError] = useState("");
  const detailRef = useRef<HTMLDivElement | null>(null);

  const selectedSheet = useMemo(
    () => review?.sheets.find((s) => s.sheet_id === selectedSheetId) ?? null,
    [review, selectedSheetId],
  );

  const currentItem = useMemo(
    () => selectedSheet?.items.find((i) => i.id === currentItemId) ?? null,
    [selectedSheet, currentItemId],
  );

  const pendingSheets = useMemo(
    () => (review?.sheets ?? []).filter((s) => s.pending_count > 0),
    [review],
  );

  const pendingIndex = useMemo(() => {
    if (!selectedSheetId) return -1;
    return pendingSheets.findIndex((s) => s.sheet_id === selectedSheetId);
  }, [pendingSheets, selectedSheetId]);

  const loadReview = useCallback(
    async (id: number, selectSheet?: number | null) => {
      const data = await api<BatchReviewData>(
        `/batches/${id}/review?pending_only=${pendingOnly}`,
      );
      setReview(data);
      const sheets = data.sheets;
      let nextSheetId = selectSheet ?? selectedSheetId;
      if (nextSheetId == null || !sheets.some((s) => s.sheet_id === nextSheetId)) {
        const paramSheet = searchParams.get("sheet");
        const fromParam = paramSheet ? Number(paramSheet) : null;
        if (fromParam && sheets.some((s) => s.sheet_id === fromParam)) {
          nextSheetId = fromParam;
        } else {
          nextSheetId = sheets.find((s) => s.pending_count > 0)?.sheet_id ?? sheets[0]?.sheet_id ?? null;
        }
      }
      setSelectedSheetId(nextSheetId);
      const sheet = sheets.find((s) => s.sheet_id === nextSheetId);
      setCurrentItemId(sheet?.items[0]?.id ?? null);
      setOverride("");
      await refreshPending();
    },
    [pendingOnly, refreshPending, searchParams, selectedSheetId],
  );

  useEffect(() => {
    initBusy.run(async () => {
      const paramBatch = searchParams.get("batch");
      if (paramBatch) {
        setScope((s) => ({ ...s, batchId: Number(paramBatch) }));
      }
    }).catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    if (scope.batchId == null) {
      setReview(null);
      return;
    }
    loadBusy
      .run(() => loadReview(scope.batchId!))
      .catch((e) => setError((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope.batchId, pendingOnly]);

  useEffect(() => {
    if (scope.batchId == null) return;
    const params = new URLSearchParams(searchParams);
    if (scope.programId != null) params.set("program", String(scope.programId));
    if (scope.sessionId != null) params.set("session", String(scope.sessionId));
    params.set("batch", String(scope.batchId));
    if (selectedSheetId != null) params.set("sheet", String(selectedSheetId));
    setSearchParams(params, { replace: true });
  }, [scope, selectedSheetId, searchParams, setSearchParams]);

  useEffect(() => {
    if (!currentItem) return;
    setAddToRoster(true);
    setRosterName("");
    setClassSection("");
    setBatchLabel("");
    if (isRollType(currentItem.anomaly_type)) {
      setOverride(currentItem.detected_values ?? currentItem.roll_no ?? "");
    } else {
      setOverride("");
    }
  }, [currentItem?.id]);

  const selectSheet = (sheetId: number) => {
    setSelectedSheetId(sheetId);
    const sheet = review?.sheets.find((s) => s.sheet_id === sheetId);
    setCurrentItemId(sheet?.items[0]?.id ?? null);
    setOverride("");
  };

  const advanceAfterResolve = useCallback(
    async (resolvedSheetId: number, resolvedItemId: number) => {
      if (scope.batchId == null) return;
      const data = await api<BatchReviewData>(
        `/batches/${scope.batchId}/review?pending_only=${pendingOnly}`,
      );
      setReview(data);
      await refreshPending();

      const sheet = data.sheets.find((s) => s.sheet_id === resolvedSheetId);
      const remaining = sheet?.items.filter((i) => i.id !== resolvedItemId) ?? [];
      if (remaining.length > 0) {
        setSelectedSheetId(resolvedSheetId);
        setCurrentItemId(remaining[0].id);
        setOverride("");
        return;
      }

      const nextPending = data.sheets.find((s) => s.pending_count > 0);
      if (nextPending) {
        setSelectedSheetId(nextPending.sheet_id);
        setCurrentItemId(nextPending.items[0]?.id ?? null);
        setOverride("");
        toast.success("Roll cleared — next sheet loaded.");
      } else {
        setSelectedSheetId(null);
        setCurrentItemId(null);
        toast.success("Batch review complete.");
      }
    },
    [scope.batchId, pendingOnly, refreshPending, toast],
  );

  const resolve = useCallback(
    async (action: string, value?: string) => {
      if (!currentItem || scope.batchId == null) return;
      setError("");
      try {
        await resolveBusy.run(async () => {
          const body: Record<string, unknown> = { action, resolved_value: value };
          if (isRollType(currentItem.anomaly_type) && action === "confirm") {
            body.add_to_roster = addToRoster;
            if (rosterName.trim()) body.roster_name = rosterName.trim();
            if (classSection.trim()) body.class_section = classSection.trim();
            if (batchLabel.trim()) body.batch_label = batchLabel.trim();
          }
          await api(`/verification/${currentItem.id}/resolve`, {
            method: "POST",
            body: JSON.stringify(body),
          });
          await advanceAfterResolve(currentItem.sheet_id, currentItem.id);
        });
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [
      currentItem,
      scope.batchId,
      resolveBusy,
      addToRoster,
      rosterName,
      classSection,
      batchLabel,
      advanceAfterResolve,
    ],
  );

  const goToAdjacentSheet = (direction: -1 | 1) => {
    if (!selectedSheetId || pendingSheets.length === 0) return;
    const idx = pendingSheets.findIndex((s) => s.sheet_id === selectedSheetId);
    const nextIdx = idx < 0 ? 0 : (idx + direction + pendingSheets.length) % pendingSheets.length;
    if (direction === 1 && idx >= 0 && idx === pendingSheets.length - 1) return;
    if (direction === -1 && idx <= 0) return;
    selectSheet(pendingSheets[nextIdx].sheet_id);
  };

  useEffect(() => {
    if (!currentItem) return;
    if (isSheetExcludeType(currentItem.anomaly_type)) return;
    const handler = (e: KeyboardEvent) => {
      if (isEditableTarget(e.target)) return;
      if (e.key === "ArrowLeft") {
        goToAdjacentSheet(-1);
        return;
      }
      if (e.key === "ArrowRight") {
        goToAdjacentSheet(1);
        return;
      }
      if (e.key === "Enter") {
        if (isAckType(currentItem.anomaly_type)) {
          resolve("confirm");
          return;
        }
        if (override) resolve("confirm", override);
        return;
      }
      if (isRollType(currentItem.anomaly_type) || isAckType(currentItem.anomaly_type)) return;
      const k = e.key.toUpperCase();
      if (["A", "B", "C", "D"].includes(k)) setOverride(k);
      else if (e.key === "0") setOverride("BLANK");
      else if (k === "S") resolve("skip");
      else if (k === "F") resolve("flag");
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [currentItem, override, resolve]);

  const isRoll = currentItem ? isRollType(currentItem.anomaly_type) : false;
  const isExcludeOnly = currentItem ? isSheetExcludeType(currentItem.anomaly_type) : false;
  const isAck = currentItem ? isAckType(currentItem.anomaly_type) : false;

  const Wrapper = embedded ? "div" : "section";

  return (
    <Wrapper>
      {!embedded && (
        <>
          <h1 className="page-title">Results</h1>
          <p className="page-subtitle">
            Review flagged sheets by roll number. Select a row, fix each flag, then use Prev/Next to
            move between rolls.
          </p>
        </>
      )}

      <SectionMessage appearance="error">{error}</SectionMessage>

      <ExamScopePicker
        levels="program+session+batch"
        value={scope}
        onChange={setScope}
        className="mb-6"
      />

      {review && (
        <div className="row-between mb-6">
          <Lozenge appearance={review.total_pending ? "warning" : "success"}>
            {review.total_pending} pending across {review.sheets_needing_review} sheets
          </Lozenge>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={pendingOnly}
              onChange={(e) => setPendingOnly(e.target.checked)}
            />
            Needs review only
          </label>
        </div>
      )}

      <details className="keyboard-help-pinned">
        <summary>Keyboard shortcuts</summary>
        <div className="keyboard-help-grid">
          <span>
            <kbd>A</kbd>–<kbd>D</kbd> Select option
          </span>
          <span>
            <kbd>0</kbd> Blank
          </span>
          <span>
            <kbd>Enter</kbd> Confirm / Sheet OK
          </span>
          <span>
            <kbd>←</kbd>/<kbd>→</kbd> Prev / next roll
          </span>
          <span>
            <kbd>S</kbd> Skip
          </span>
          <span>
            <kbd>F</kbd> Flag
          </span>
        </div>
      </details>

      {(initBusy.busy || loadBusy.busy) && <Spinner label="Loading batch review…" />}

      {scope.batchId != null && !loadBusy.busy && review && review.sheets.length === 0 && (
        <EmptyState
          title="All clear"
          description="No sheets need review in this batch."
          action={
            <Link to="/">
              <Button variant="default">Back to Run exam</Button>
            </Link>
          }
        />
      )}

      {review && review.sheets.length > 0 && (
        <div className="verify-grid">
          <div className="batch-review-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Roll</th>
                  <th>Source</th>
                  <th>Flags</th>
                  <th>Pending</th>
                </tr>
              </thead>
              <tbody>
                {review.sheets.map((s) => (
                  <tr
                    key={s.sheet_id}
                    className={
                      s.sheet_id === selectedSheetId
                        ? "batch-review-row batch-review-row--active"
                        : "batch-review-row"
                    }
                    onClick={() => selectSheet(s.sheet_id)}
                  >
                    <td>{s.roll_no ?? "—"}</td>
                    <td className="muted">{s.source_file ?? "—"}</td>
                    <td>
                      <span className="batch-review-flags">
                        {s.flags.map((f, i) => (
                          <Lozenge key={`${f.type}-${f.global_q ?? i}`} appearance="warning">
                            {f.label}
                          </Lozenge>
                        ))}
                        {s.flags.length === 0 && <span className="muted">—</span>}
                      </span>
                    </td>
                    <td>{s.pending_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selectedSheet && (
            <div ref={detailRef} className="batch-review-detail" tabIndex={-1}>
              <div className="row-between mb-5">
                <h2 style={{ margin: 0 }}>
                  Roll {selectedSheet.roll_no ?? "?"}
                  {selectedSheet.source_file && (
                    <span className="muted"> · {selectedSheet.source_file}</span>
                  )}
                </h2>
                <div className="row">
                  <Button
                    variant="subtle"
                    onClick={() => goToAdjacentSheet(-1)}
                    disabled={pendingSheets.length < 2}
                  >
                    Prev roll
                  </Button>
                  <Button
                    variant="subtle"
                    onClick={() => goToAdjacentSheet(1)}
                    disabled={pendingSheets.length < 2}
                  >
                    Next roll
                  </Button>
                </div>
              </div>

              <p className="muted mb-5">
                <Lozenge appearance={statusAppearance(selectedSheet.status)}>
                  {selectedSheet.status.replace(/_/g, " ")}
                </Lozenge>
                {selectedSheet.alignment_quality != null && (
                  <> · alignment {selectedSheet.alignment_quality}</>
                )}
                {selectedSheet.pending_count > 0 && (
                  <> · {selectedSheet.pending_count} flag(s) pending</>
                )}
                {currentItem?.has_source_image && (
                  <>
                    {" "}
                    ·{" "}
                    <a href={`/api/sheets/${selectedSheet.sheet_id}/source-image`} target="_blank" rel="noreferrer">
                      View scan
                    </a>
                  </>
                )}
              </p>

              {selectedSheet.items.length === 0 ? (
                <SectionMessage appearance="info">No pending flags on this sheet.</SectionMessage>
              ) : (
                <ul className="queue-list">
                  {selectedSheet.items.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        className={
                          item.id === currentItemId ? "queue-item active" : "queue-item"
                        }
                        onClick={() => setCurrentItemId(item.id)}
                      >
                        <Lozenge appearance="warning">{item.anomaly_type}</Lozenge>
                        {item.global_question_no > 0 && (
                          <span className="muted">Q{item.global_question_no}</span>
                        )}
                        <span className="muted">{item.detected_values ?? "-"}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {currentItem && (
                <div className="mt-6">
                  {currentItem.anomaly_type === "alignment_failed" &&
                    (currentItem.has_source_image ? (
                      <img
                        className="crop-img"
                        src={`/api/sheets/${currentItem.sheet_id}/source-image`}
                        alt="source scan"
                      />
                    ) : (
                      <SectionMessage appearance="info">No source scan image available.</SectionMessage>
                    ))}

                  {currentItem.anomaly_type !== "alignment_failed" && currentItem.has_crop && (
                    <img
                      className="crop-img"
                      src={`/api/verification/${currentItem.id}/crop`}
                      alt="anomaly crop"
                    />
                  )}

                  {isRoll && (
                    <>
                      <input
                        autoFocus
                        value={override}
                        placeholder="e.g. 014532"
                        onChange={(e) => setOverride(e.target.value)}
                        className="mb-5"
                      />
                      <details className="disclosure mb-5">
                        <summary>Roster entry</summary>
                        <label className="checkbox-row">
                          <input
                            type="checkbox"
                            checked={addToRoster}
                            onChange={(e) => setAddToRoster(e.target.checked)}
                          />
                          Add to roster
                        </label>
                        <input
                          value={rosterName}
                          placeholder="Name (defaults to roll)"
                          onChange={(e) => setRosterName(e.target.value)}
                          className="mb-4"
                        />
                        <input
                          value={classSection}
                          placeholder="Class (optional)"
                          onChange={(e) => setClassSection(e.target.value)}
                          className="mb-4"
                        />
                        <input
                          value={batchLabel}
                          placeholder="Batch (optional)"
                          onChange={(e) => setBatchLabel(e.target.value)}
                        />
                      </details>
                    </>
                  )}

                  {!isRoll && !isExcludeOnly && !isAck && (
                    <OptionToggleGroup
                      options={MCQ_OPTIONS}
                      value={override}
                      onChange={setOverride}
                      disabled={resolveBusy.busy}
                    />
                  )}

                  <div className="review-action-bar">
                    {pendingIndex >= 0 && pendingSheets.length > 0 && (
                      <span className="review-progress">
                        Sheet {pendingIndex + 1} of {pendingSheets.length} pending
                      </span>
                    )}
                    {isExcludeOnly ? (
                      <>
                        <Button
                          variant="primary"
                          className="btn-touch"
                          onClick={() => resolve("exclude")}
                          disabled={resolveBusy.busy}
                        >
                          {resolveBusy.busy ? "Saving…" : "Exclude sheet"}
                        </Button>
                        <Button variant="subtle" className="btn-touch" onClick={() => resolve("skip")} disabled={resolveBusy.busy}>
                          Skip
                        </Button>
                      </>
                    ) : isAck ? (
                      <>
                        <Button
                          variant="primary"
                          className="btn-touch"
                          onClick={() => resolve("confirm")}
                          disabled={resolveBusy.busy}
                        >
                          {resolveBusy.busy ? "Saving…" : "Sheet OK"}
                        </Button>
                        <Button variant="subtle" className="btn-touch" onClick={() => resolve("skip")} disabled={resolveBusy.busy}>
                          Skip
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          variant="primary"
                          className="btn-touch"
                          onClick={() => resolve("confirm", override)}
                          disabled={!override || resolveBusy.busy}
                        >
                          {resolveBusy.busy ? "Saving…" : "Confirm"}
                        </Button>
                        <Button variant="subtle" className="btn-touch" onClick={() => resolve("skip")} disabled={resolveBusy.busy}>
                          Skip
                        </Button>
                        <Button variant="subtle" className="btn-touch" onClick={() => resolve("flag")} disabled={resolveBusy.busy}>
                          Flag
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </Wrapper>
  );
}
