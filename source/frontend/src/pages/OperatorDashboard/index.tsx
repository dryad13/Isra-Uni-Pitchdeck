import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, upload } from "../../lib/api";
import Button from "../../components/Button";
import Field from "../../components/Field";
import Tabs from "../../components/Tabs";
import PageLayout from "../../components/PageLayout";
import { useToast } from "../../components/Toast";
import { useBusy } from "../../hooks/useBusy";
import Stepper, { deriveStepStates } from "./Stepper";
import StepExamSession from "./StepExamSession";
import StepAnswerKey from "./StepAnswerKey";
import StepScanning from "./StepScanning";
import ExamManagement from "./ExamManagement";
import type {
  BatchSummary,
  IngestionStatus,
  KeyStatus,
  NewSessionForm,
  Program,
  ProgramDetail,
  SessionRow,
  SubjectSplit,
} from "./types";
import { SHEET_TYPES } from "./types";

export default function OperatorDashboard() {
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const viewMode = searchParams.get("view") === "manage" ? "manage" : "workflow";
  const setViewMode = (mode: "workflow" | "manage") => {
    const params = new URLSearchParams(searchParams);
    if (mode === "manage") params.set("view", "manage");
    else params.delete("view");
    setSearchParams(params, { replace: true });
  };
  const initBusy = useBusy();
  const programBusy = useBusy();
  const sessionBusy = useBusy();
  const deleteBusy = useBusy();
  const uploadSheetBusy = useBusy();
  const uploadFileBusy = useBusy();
  const saveManualBusy = useBusy();
  const startBusy = useBusy();
  const stopBusy = useBusy();
  const uploadScanBusy = useBusy();

  const [programs, setPrograms] = useState<Program[]>([]);
  const [selectedProgramId, setSelectedProgramId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [subjects, setSubjects] = useState<SubjectSplit[]>([]);
  const [suggestedStart, setSuggestedStart] = useState(1);

  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [keyStatus, setKeyStatus] = useState<KeyStatus | null>(null);
  const [keyDraft, setKeyDraft] = useState<Record<number, string>>({});

  const [ingestion, setIngestion] = useState<IngestionStatus | null>(null);
  const [lastBatchSummary, setLastBatchSummary] = useState<BatchSummary | null>(null);
  const [interruptedBatch, setInterruptedBatch] = useState<BatchSummary | null>(null);

  const [newProgramName, setNewProgramName] = useState("");
  const [newSession, setNewSession] = useState<NewSessionForm>({
    name: "",
    template_family: "150Q",
    scan_template_family: null,
    sheet_question_count: "20",
    negative_marking_ratio: "0",
  });
  const [expectedCount, setExpectedCount] = useState("");
  const [newSubject, setNewSubject] = useState({ name: "", q_start: "", q_end: "" });

  const [error, setError] = useState("");

  const selectedSession = sessions.find((s) => s.id === selectedSessionId) ?? null;

  const loadPrograms = useCallback(async () => {
    const data = await api<{ programs: Program[] }>("/programs");
    setPrograms(data.programs);
    return data.programs;
  }, []);

  const loadDetail = useCallback(async (id: number) => {
    const data = await api<ProgramDetail & { subjects?: SubjectSplit[] }>(`/programs/${id}`);
    setSessions(data.sessions);
    setSubjects(data.subjects ?? []);
    const sug = await api<{ global_q_start: number }>(`/programs/${id}/sessions/suggest-start`);
    setSuggestedStart(sug.global_q_start);
  }, []);

  useEffect(() => {
    initBusy
      .run(async () => {
        const loaded =         await loadPrograms();
        setIngestion(await api<IngestionStatus>("/ingestion/status"));

        const preProgram = searchParams.get("program");
        if (preProgram) {
          const pid = Number(preProgram);
          if (loaded.some((p) => p.id === pid)) {
            setSelectedProgramId(pid);
          }
        }
      })
      .catch((e) => setError((e as Error).message));
  }, [loadPrograms, searchParams]);

  useEffect(() => {
    setSessions([]);
    setSelectedSessionId(null);
    setKeyStatus(null);
    if (selectedProgramId != null) {
      loadDetail(selectedProgramId).catch((e) => setError((e as Error).message));
    }
  }, [selectedProgramId, loadDetail]);

  useEffect(() => {
    const preSession = searchParams.get("session");
    if (!preSession || sessions.length === 0) return;
    const sid = Number(preSession);
    if (sessions.some((s) => s.id === sid)) {
      setSelectedSessionId(sid);
    }
  }, [sessions, searchParams]);

  const loadKeyStatus = useCallback(async (sessionId: number) => {
    const st = await api<KeyStatus>(`/sessions/${sessionId}/key-status`);
    setKeyStatus(st);
    const draft: Record<number, string> = {};
    st.keys.forEach((k) => (draft[k.question_no] = k.correct_option));
    setKeyDraft(draft);
  }, []);

  useEffect(() => {
    if (selectedSessionId == null) {
      setKeyStatus(null);
      setKeyDraft({});
      return;
    }
    loadKeyStatus(selectedSessionId).catch((e) => setError((e as Error).message));
  }, [selectedSessionId, loadKeyStatus]);

  const watching = ingestion?.watching ?? false;
  const ingestionTimer = useRef<number | null>(null);
  useEffect(() => {
    if (!watching) return;
    const tick = async () => {
      try {
        const status = await api<IngestionStatus>("/ingestion/status");
        setIngestion(status);
        if (status.last_batch_id != null) {
          const batch = await api<BatchSummary>(`/batches/${status.last_batch_id}`);
          setLastBatchSummary(batch);
        } else {
          setLastBatchSummary(null);
        }
      } catch {
        /* ignore */
      }
    };
    ingestionTimer.current = window.setInterval(tick, 2000);
    void tick();
    return () => {
      if (ingestionTimer.current) window.clearInterval(ingestionTimer.current);
    };
  }, [watching]);

  const createProgram = () =>
    programBusy.run(async () => {
      setError("");
      const created = await api<Program>("/programs", {
        method: "POST",
        body: JSON.stringify({ name: newProgramName }),
      });
      setNewProgramName("");
      await loadPrograms();
      setSelectedProgramId(created.id);
      toast.success(`Created exam "${created.name}".`);
    }).catch((e) => setError((e as Error).message));

  const createSession = () => {
    if (selectedProgramId == null) return Promise.resolve();
    return sessionBusy.run(async () => {
      setError("");
      const sheetMax =
        SHEET_TYPES.find((s) => s.value === newSession.template_family)?.maxQuestions ?? 150;
      const count = Math.min(
        sheetMax,
        Math.max(1, Math.floor(Number(newSession.sheet_question_count) || 1)),
      );
      await api(`/programs/${selectedProgramId}/sessions`, {
        method: "POST",
        body: JSON.stringify({
          name: newSession.name,
          template_family: newSession.template_family,
          scan_template_family: newSession.scan_template_family,
          sheet_question_count: count,
          negative_marking_ratio: Number(newSession.negative_marking_ratio) || 0,
        }),
      });
      setNewSession({ ...newSession, name: "" });
      await loadDetail(selectedProgramId);
      toast.success("Session added.");
    }).catch((e) => setError((e as Error).message));
  };

  const deleteSession = (id: number) => {
    if (selectedProgramId == null) return Promise.resolve();
    return deleteBusy.run(async () => {
      setError("");
      await api(`/sessions/${id}`, { method: "DELETE" });
      if (selectedSessionId === id) setSelectedSessionId(null);
      await loadDetail(selectedProgramId);
      toast.success("Session deleted.");
    }).catch((e) => setError((e as Error).message));
  };

  const uploadKeys = (fileList: FileList | null) => {
    if (selectedProgramId == null || selectedSessionId == null || !fileList?.length)
      return Promise.resolve();
    return uploadFileBusy.run(async () => {
      setError("");
      const form = new FormData();
      form.append("file", fileList[0]);
      form.append("session_id", String(selectedSessionId));
      const result = await upload<{ created: number; updated: number }>(
        `/programs/${selectedProgramId}/answer-keys/upload`,
        form,
      );
      toast.success(`Uploaded answer key (${result.created} added, ${result.updated} updated).`);
      await loadKeyStatus(selectedSessionId);
      await loadDetail(selectedProgramId);
    }).catch((e) => setError((e as Error).message));
  };

  const uploadKeySheet = (fileList: FileList | null) => {
    if (selectedProgramId == null || selectedSessionId == null || !fileList?.length)
      return Promise.resolve();
    return uploadSheetBusy.run(async () => {
      setError("");
      const form = new FormData();
      form.append("file", fileList[0]);
      form.append("session_id", String(selectedSessionId));
      const result = await upload<{ created: number; updated: number; extracted?: unknown[] }>(
        `/programs/${selectedProgramId}/answer-keys/upload`,
        form,
      );
      const n = result.extracted?.length ?? result.created + result.updated;
      toast.success(
        `Read answer key from sheet (${n} questions, ${result.created} added, ${result.updated} updated).`,
      );
      await loadKeyStatus(selectedSessionId);
      await loadDetail(selectedProgramId);
    }).catch((e) => setError((e as Error).message));
  };

  const saveManualKeys = () => {
    if (selectedProgramId == null || selectedSessionId == null || !keyStatus) return Promise.resolve();
    const entries = Object.entries(keyDraft)
      .filter(([, opt]) => opt)
      .map(([q, opt]) => ({ question_no: Number(q), correct_option: opt }));
    if (entries.length === 0) return Promise.resolve();
    return saveManualBusy.run(async () => {
      setError("");
      const res = await api<{ created: number; updated: number }>(
        `/programs/${selectedProgramId}/answer-keys`,
        { method: "POST", body: JSON.stringify({ entries, session_id: selectedSessionId }) },
      );
      toast.success(`Saved key (${res.created} added, ${res.updated} updated).`);
      await loadKeyStatus(selectedSessionId);
      await loadDetail(selectedProgramId);
    }).catch((e) => setError((e as Error).message));
  };

  useEffect(() => {
    if (selectedSessionId == null) {
      setInterruptedBatch(null);
      return;
    }
    const loadInterrupted = async () => {
      try {
        const data = await api<{ batches: BatchSummary[] }>(
          `/sessions/${selectedSessionId}/batches?status=interrupted`,
        );
        const candidate = data.batches.find((b) => b.can_resume) ?? null;
        setInterruptedBatch(candidate);
      } catch {
        setInterruptedBatch(null);
      }
    };
    void loadInterrupted();
    const timer = window.setInterval(loadInterrupted, 5000);
    return () => window.clearInterval(timer);
  }, [selectedSessionId]);

  const resumeBatch = (batchId: number) =>
    startBusy.run(async () => {
      setError("");
      await api(`/batches/${batchId}/resume`, { method: "POST" });
      toast.success(`Resuming batch #${batchId}.`);
      const batch = await api<BatchSummary>(`/batches/${batchId}`);
      setLastBatchSummary(batch);
      setInterruptedBatch(null);
    }).catch((e) => setError((e as Error).message));

  const startScanning = () => {
    if (selectedSessionId == null) return Promise.resolve();
    return startBusy.run(async () => {
      setError("");
      const payload: { session_id: number; expected_count?: number } = {
        session_id: selectedSessionId,
      };
      const expected = Number(expectedCount);
      if (Number.isFinite(expected) && expected > 0) {
        payload.expected_count = expected;
      }
      await api("/ingestion/start", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setIngestion(await api<IngestionStatus>("/ingestion/status"));
      toast.success("Processing started. Drop scans into the dropzone folder.");
    }).catch((e) => setError((e as Error).message));
  };

  const stopScanning = () =>
    stopBusy.run(async () => {
      setError("");
      await api("/ingestion/stop", { method: "POST" });
      setIngestion(await api<IngestionStatus>("/ingestion/status"));
      toast.info("Processing stopped.");
    }).catch((e) => setError((e as Error).message));

  const uploadScan = (filesInput: File[] | FileList) => {
    const files = filesInput instanceof FileList ? Array.from(filesInput) : filesInput;
    const validFiles = files.filter((f) => /\.(jpg|jpeg|png|tif|tiff|pdf)$/i.test(f.name));
    if (selectedSessionId == null || validFiles.length === 0) {
      if (files.length > 0 && validFiles.length === 0) {
        toast.error("No valid scan files (.jpg, .jpeg, .png, .tif, .pdf) found in selection.");
      }
      return Promise.resolve();
    }

    return uploadScanBusy.run(async () => {
      setError("");
      const watchingThis =
        ingestion?.watching && ingestion.active_session_id === selectedSessionId;
      if (!watchingThis) {
        const payload: { session_id: number; expected_count?: number } = {
          session_id: selectedSessionId,
        };
        const expected = Number(expectedCount);
        if (Number.isFinite(expected) && expected > 0) {
          payload.expected_count = expected;
        }
        await api("/ingestion/start", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }

      let uploadedCount = 0;
      for (const file of validFiles) {
        const form = new FormData();
        form.append("file", file);
        setIngestion(await upload<IngestionStatus>("/ingestion/upload", form));
        uploadedCount++;
      }
      toast.success(`Uploaded ${uploadedCount} scan file${uploadedCount > 1 ? "s" : ""} for processing.`);
    }).catch((e) => setError((e as Error).message));
  };

  const addSubject = () => {
    if (selectedProgramId == null) return Promise.resolve();
    return sessionBusy.run(async () => {
      setError("");
      await api(`/programs/${selectedProgramId}/subjects`, {
        method: "POST",
        body: JSON.stringify({
          subject_name: newSubject.name,
          q_start: Number(newSubject.q_start),
          q_end: Number(newSubject.q_end),
        }),
      });
      setNewSubject({ name: "", q_start: "", q_end: "" });
      await loadDetail(selectedProgramId);
      toast.success("Subject split added.");
    }).catch((e) => setError((e as Error).message));
  };

  const deleteSubject = (splitId: number) => {
    if (selectedProgramId == null) return Promise.resolve();
    return deleteBusy.run(async () => {
      setError("");
      await api(`/programs/subjects/${splitId}`, { method: "DELETE" });
      await loadDetail(selectedProgramId);
      toast.success("Subject split removed.");
    }).catch((e) => setError((e as Error).message));
  };

  const keyReady = keyStatus?.ready ?? false;
  const keyTotal =
    keyStatus?.total ??
    (selectedSession
      ? selectedSession.key_total ??
        selectedSession.global_q_end - selectedSession.global_q_start + 1
      : 0);

  const keyFilled = useMemo(() => {
    if (!selectedSession) return 0;
    const start = keyStatus?.global_q_start ?? selectedSession.global_q_start;
    const end = keyStatus?.global_q_end ?? selectedSession.global_q_end;
    let count = 0;
    for (let q = start; q <= end; q++) {
      if (keyDraft[q]?.trim()) count++;
    }
    return count;
  }, [keyStatus, keyDraft, selectedSession]);

  const scanningThisSession =
    watching && ingestion?.active_session_id === selectedSessionId && selectedSessionId != null;

  const [s1, s2, s3] = deriveStepStates(
    selectedSessionId != null,
    keyReady,
    scanningThisSession,
  );

  return (
    <PageLayout
      title="Run exam"
      subtitle={
        viewMode === "workflow"
          ? "Pick an exam, load its answer key, then process scanned sheets. Flagged sheets go to Results for review."
          : "Browse all exam programs, view session counts, and jump to setup or roster."
      }
      error={error}
    >
      <Tabs
        className="mode-tabs"
        variant="toolbar"
        ariaLabel="Run exam mode"
        items={[
          { id: "workflow", label: "Run workflow" },
          { id: "manage", label: "Manage exams" },
        ]}
        activeId={viewMode}
        onChange={(id) => setViewMode(id as "workflow" | "manage")}
      />

      {viewMode === "manage" ? (
        <div className="dashboard-mode-content">
          <ExamManagement />
        </div>
      ) : (
        <div className="dashboard-mode-content">
      <Stepper step1={s1} step2={s2} step3={s3} />

      <StepExamSession
        programs={programs}
        selectedProgramId={selectedProgramId}
        onSelectProgram={setSelectedProgramId}
        newProgramName={newProgramName}
        onNewProgramName={setNewProgramName}
        onCreateProgram={createProgram}
        creatingProgram={programBusy.busy}
        sessions={sessions}
        selectedSessionId={selectedSessionId}
        onSelectSession={setSelectedSessionId}
        onDeleteSession={deleteSession}
        deletingSession={deleteBusy.busy}
        newSession={newSession}
        onNewSession={setNewSession}
        suggestedStart={suggestedStart}
        onCreateSession={createSession}
        creatingSession={sessionBusy.busy}
        loading={initBusy.busy}
      />

      {selectedProgramId != null && (
        <div className="panel mt-6">
          <details className="disclosure">
            <summary>Subject splits (optional)</summary>
            <p className="muted mb-5">
              Define global question ranges for per-subject scores in exports.
            </p>
            {subjects.length > 0 && (
              <table className="data-table mb-5">
                <thead>
                  <tr>
                    <th>Subject</th>
                    <th>Range</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {subjects.map((s) => (
                    <tr key={s.id}>
                      <td>{s.subject_name}</td>
                      <td>
                        Q{s.q_start}&ndash;Q{s.q_end}
                      </td>
                      <td>
                        <Button variant="danger-link" onClick={() => deleteSubject(s.id)}>
                          delete
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="field-row">
              <Field label="Name" htmlFor="subj-name">
                <input
                  id="subj-name"
                  value={newSubject.name}
                  onChange={(e) => setNewSubject({ ...newSubject, name: e.target.value })}
                  placeholder="e.g. Physics"
                />
              </Field>
              <Field label="Q start" htmlFor="subj-start">
                <input
                  id="subj-start"
                  type="number"
                  min={1}
                  value={newSubject.q_start}
                  onChange={(e) => setNewSubject({ ...newSubject, q_start: e.target.value })}
                />
              </Field>
              <Field label="Q end" htmlFor="subj-end">
                <input
                  id="subj-end"
                  type="number"
                  min={1}
                  value={newSubject.q_end}
                  onChange={(e) => setNewSubject({ ...newSubject, q_end: e.target.value })}
                />
              </Field>
              <Button
                onClick={addSubject}
                disabled={
                  !newSubject.name ||
                  !newSubject.q_start ||
                  !newSubject.q_end ||
                  sessionBusy.busy
                }
              >
                Add subject
              </Button>
            </div>
          </details>
        </div>
      )}

      <StepAnswerKey
        selectedSession={selectedSession}
        keyStatus={keyStatus}
        keyDraft={keyDraft}
        onKeyDraftChange={setKeyDraft}
        keyReady={keyReady}
        keyFilled={keyFilled}
        keyTotal={keyTotal}
        onUploadSheet={uploadKeySheet}
        onUploadFile={uploadKeys}
        onSaveManual={saveManualKeys}
        uploadingSheet={uploadSheetBusy.busy}
        uploadingFile={uploadFileBusy.busy}
        savingManual={saveManualBusy.busy}
      />

      <StepScanning
        keyReady={keyReady}
        scanningThisSession={scanningThisSession}
        watching={watching}
        ingestion={ingestion}
        lastBatchSummary={lastBatchSummary}
        expectedCount={expectedCount}
        onExpectedCountChange={setExpectedCount}
        onStartScanning={startScanning}
        onStopScanning={stopScanning}
        onUploadScan={uploadScan}
        onResumeBatch={resumeBatch}
        interruptedBatch={interruptedBatch}
        starting={startBusy.busy}
        stopping={stopBusy.busy}
        uploading={uploadScanBusy.busy}
      />

      <div className={`dashboard-footer${scanningThisSession ? " dashboard-footer-sticky" : ""}`}>
        <Link to="/verify">
          <Button variant="subtle">Go to Results</Button>
        </Link>
        <Link to="/export">
          <Button variant="subtle">Reports</Button>
        </Link>
      </div>
        </div>
      )}
    </PageLayout>
  );
}
