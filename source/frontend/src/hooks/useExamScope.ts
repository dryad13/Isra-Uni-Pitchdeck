import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";

export type ScopeLevel = "program" | "program+session" | "program+session+batch";

export type Program = { id: number; name: string };
export type SessionRow = { id: number; name: string; global_q_start?: number; global_q_end?: number };
export type BatchRow = { id: number; status: string; pending_verifications?: number };

export type ExamScopeValue = {
  programId: number | null;
  sessionId: number | null;
  batchId: number | null;
};

type Options = {
  levels: ScopeLevel;
  syncUrl?: boolean;
  initial?: Partial<ExamScopeValue>;
};

function readParam(searchParams: URLSearchParams, key: string) {
  const v = searchParams.get(key);
  if (!v) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export function useExamScope({ levels, syncUrl = false, initial }: Options) {
  const [searchParams, setSearchParams] = useSearchParams();

  const [programs, setPrograms] = useState<Program[]>([]);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [batches, setBatches] = useState<BatchRow[]>([]);
  const [programId, setProgramId] = useState<number | null>(
    initial?.programId ?? (syncUrl ? readParam(searchParams, "program") : null),
  );
  const [sessionId, setSessionId] = useState<number | null>(
    initial?.sessionId ?? (syncUrl ? readParam(searchParams, "session") : null),
  );
  const [batchId, setBatchId] = useState<number | null>(
    initial?.batchId ?? (syncUrl ? readParam(searchParams, "batch") : null),
  );
  const [loading, setLoading] = useState(true);

  const needsSession =
    levels === "program+session" || levels === "program+session+batch";
  const needsBatch = levels === "program+session+batch";

  useEffect(() => {
    api<{ programs: Program[] }>("/programs")
      .then((data) => setPrograms(data.programs))
      .catch(() => setPrograms([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!needsSession || programId == null) {
      setSessions([]);
      return;
    }
    api<{ sessions: SessionRow[] }>(`/programs/${programId}/sessions`)
      .then((data) => setSessions(data.sessions))
      .catch(() => setSessions([]));
  }, [programId, needsSession]);

  useEffect(() => {
    if (!needsBatch || sessionId == null) {
      setBatches([]);
      return;
    }
    api<{ batches: BatchRow[] }>(`/sessions/${sessionId}/batches`)
      .then((data) => setBatches(data.batches))
      .catch(() => setBatches([]));
  }, [sessionId, needsBatch]);

  const syncToUrl = useCallback(
    (next: ExamScopeValue) => {
      if (!syncUrl) return;
      const params = new URLSearchParams(searchParams);
      if (next.programId != null) params.set("program", String(next.programId));
      else params.delete("program");
      if (next.sessionId != null) params.set("session", String(next.sessionId));
      else params.delete("session");
      if (next.batchId != null) params.set("batch", String(next.batchId));
      else params.delete("batch");
      setSearchParams(params, { replace: true });
    },
    [searchParams, setSearchParams, syncUrl],
  );

  const setScope = useCallback(
    (patch: Partial<ExamScopeValue>) => {
      let nextProgram = programId;
      let nextSession = sessionId;
      let nextBatch = batchId;

      if (patch.programId !== undefined) {
        nextProgram = patch.programId;
        if (patch.programId !== programId) {
          nextSession = null;
          nextBatch = null;
        }
      }
      if (patch.sessionId !== undefined) {
        nextSession = patch.sessionId;
        if (patch.sessionId !== sessionId) {
          nextBatch = null;
        }
      }
      if (patch.batchId !== undefined) {
        nextBatch = patch.batchId;
      }

      setProgramId(nextProgram);
      setSessionId(nextSession);
      setBatchId(nextBatch);
      syncToUrl({ programId: nextProgram, sessionId: nextSession, batchId: nextBatch });
    },
    [batchId, programId, sessionId, syncToUrl],
  );

  const value: ExamScopeValue = { programId, sessionId, batchId };

  return {
    value,
    setScope,
    programs,
    sessions,
    batches,
    loading,
    levels,
    programId,
    sessionId,
    batchId,
    setProgramId: (id: number | null) => setScope({ programId: id }),
    setSessionId: (id: number | null) => setScope({ sessionId: id }),
    setBatchId: (id: number | null) => setScope({ batchId: id }),
  };
}
