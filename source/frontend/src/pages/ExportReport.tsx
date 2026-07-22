import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import Button from "../components/Button";
import EmptyState from "../components/EmptyState";
import ExamScopePicker from "../components/ExamScopePicker";
import Field from "../components/Field";
import PageLayout from "../components/PageLayout";
import DataTable, { type Column } from "../components/table/DataTable";
import Pagination from "../components/table/Pagination";
import TableToolbar from "../components/table/TableToolbar";
import { useToast } from "../components/Toast";
import { useBusy } from "../hooks/useBusy";
import { useTableState } from "../hooks/useTableState";
import { useExamScope } from "../hooks/useExamScope";

type Program = { id: number; name: string };

type SubjectScore = {
  subject_name: string;
  correct: number;
  percentage: number;
};

type ScoreResult = {
  sheet_id: number | null;
  roll_no: string | null;
  percentage: number;
  secure_score: number;
  counts: { correct: number; wrong: number; blank: number; multi: number; total: number };
  subjects?: SubjectScore[];
};

type SessionScores = {
  session_name: string;
  sheet_count: number;
  results: ScoreResult[];
};

export default function ExportReport() {
  const toast = useToast();
  const initBusy = useBusy();
  const scoresBusy = useBusy();
  const exportBusy = useBusy();

  const [programs, setPrograms] = useState<{ id: number; name: string }[]>([]);
  const examScope = useExamScope({ levels: "program+session" });
  const programId = examScope.programId;
  const sessions = examScope.sessions;
  const [sessionId, setSessionId] = useState<number | "program" | null>(null);
  const [mode, setMode] = useState("literal");
  const [format, setFormat] = useState("csv");
  const [scores, setScores] = useState<SessionScores | null>(null);
  const [error, setError] = useState("");
  const [minPct, setMinPct] = useState("");
  const [maxPct, setMaxPct] = useState("");
  const [issuesOnly, setIssuesOnly] = useState(false);

  useEffect(() => {
    initBusy
      .run(async () => {
        const d = await api<{ programs: Program[] }>("/programs");
        setPrograms(d.programs);
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    setScores(null);
    setSessionId(null);
  }, [programId]);

  useEffect(() => {
    if (examScope.sessionId != null && sessionId == null) {
      setSessionId(examScope.sessionId);
    }
  }, [examScope.sessionId, sessionId]);

  const loadScores = useCallback(async () => {
    if (sessionId == null) return;
    setError("");
    try {
      if (sessionId === "program" && programId != null) {
        setScores(await api<SessionScores>(`/programs/${programId}/scores`));
      } else if (typeof sessionId === "number") {
        setScores(await api<SessionScores>(`/sessions/${sessionId}/scores`));
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }, [sessionId, programId]);

  useEffect(() => {
    if (sessionId == null) {
      setScores(null);
      return;
    }
    scoresBusy.run(loadScores);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, programId]);

  const subjectNames = useMemo(() => {
    if (!scores) return [];
    const cols: string[] = [];
    for (const r of scores.results) {
      for (const s of r.subjects ?? []) {
        if (!cols.includes(s.subject_name)) cols.push(s.subject_name);
      }
    }
    return cols;
  }, [scores]);

  const filteredResults = useMemo(() => {
    if (!scores) return [];
    let rows = scores.results;
    const min = minPct ? Number(minPct) : null;
    const max = maxPct ? Number(maxPct) : null;
    if (min != null && !Number.isNaN(min)) {
      rows = rows.filter((r) => r.percentage >= min);
    }
    if (max != null && !Number.isNaN(max)) {
      rows = rows.filter((r) => r.percentage <= max);
    }
    if (issuesOnly) {
      rows = rows.filter((r) => r.counts.blank > 0 || r.counts.multi > 0);
    }
    return rows;
  }, [scores, minPct, maxPct, issuesOnly]);

  const flatResults = useMemo(
    () =>
      filteredResults.map((r) => ({
        ...r,
        correct: r.counts.correct,
        wrong: r.counts.wrong,
        blank: r.counts.blank,
        multi: r.counts.multi,
      })),
    [filteredResults],
  );

  const table = useTableState<ScoreResult & { correct: number; wrong: number; blank: number; multi: number }>({
    rows: flatResults,
    searchKeys: ["roll_no"],
    defaultSortKey: "roll_no",
  });

  const columns: Column<ScoreResult>[] = useMemo(() => {
    const base: Column<ScoreResult>[] = [
      {
        key: "roll_no",
        label: "Roll",
        sortable: true,
        render: (r) =>
          r.sheet_id != null ? (
            <Link to={`/sheets/${r.sheet_id}`} state={{ from: "reports" }}>
              {r.roll_no ?? "-"}
            </Link>
          ) : (
            (r.roll_no ?? "-")
          ),
      },
      {
        key: "correct",
        label: "Correct",
        sortable: true,
        render: (r) => r.counts.correct,
      },
      {
        key: "wrong",
        label: "Wrong",
        sortable: true,
        render: (r) => r.counts.wrong,
      },
      {
        key: "blank",
        label: "Blank",
        sortable: true,
        render: (r) => r.counts.blank,
      },
      {
        key: "multi",
        label: "Multi",
        sortable: true,
        render: (r) => r.counts.multi,
      },
      {
        key: "percentage",
        label: "%",
        sortable: true,
        render: (r) => r.percentage,
      },
      {
        key: "secure_score",
        label: "Secure",
        sortable: true,
        render: (r) => r.secure_score,
      },
    ];
    for (const name of subjectNames) {
      base.push({
        key: `${name}_correct`,
        label: `${name} C`,
        render: (r) => r.subjects?.find((s) => s.subject_name === name)?.correct ?? "-",
      });
      base.push({
        key: `${name}_pct`,
        label: `${name} %`,
        render: (r) => r.subjects?.find((s) => s.subject_name === name)?.percentage ?? "-",
      });
    }
    return base;
  }, [subjectNames]);

  const download = () => {
    if (sessionId == null) return;
    exportBusy.run(async () => {
      const base =
        sessionId === "program"
          ? `/api/programs/${programId}/export`
          : `/api/sessions/${sessionId}/export`;
      window.open(`${base}?mode=${mode}&format=${format}`, "_blank");
      toast.success(`Exporting ${format.toUpperCase()}…`);
    });
  };

  const formatLabel = format === "xlsx" ? "Excel" : "CSV";

  return (
    <PageLayout
      title="Reports"
      subtitle="Score sheets against the answer key, view the result summary, and export results. Secure Score excludes blank and multi from the denominator."
      error={error}
      loading={initBusy.busy}
      loadingLabel="Loading exams…"
      empty={
        !initBusy.busy && programs.length === 0
          ? {
              title: "No exams to report on",
              description:
                "Create an exam and process sheets first, then return here to export results.",
            }
          : null
      }
    >
      {programs.length > 0 && (
        <div className="panel">
          <ExamScopePicker
            levels="program+session"
            value={examScope.value}
            onChange={(v) => {
              examScope.setScope(v);
              if (v.sessionId != null) setSessionId(v.sessionId);
            }}
            className="mb-5"
          />

          <div className="field-row">
            <Field label="Scope" htmlFor="exp-scope">
              <select
                id="exp-scope"
                value={sessionId ?? ""}
                onChange={(e) => {
                  const v = e.target.value;
                  setSessionId(v === "" ? null : v === "program" ? "program" : Number(v));
                }}
                disabled={programId == null}
              >
                <option value="">Select a scope</option>
                <option value="program">Whole program (cumulative)</option>
                {sessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} (Q{s.global_q_start}&ndash;Q{s.global_q_end})
                  </option>
                ))}
              </select>
            </Field>

            <Button
              variant="primary"
              className="btn-touch"
              onClick={download}
              disabled={sessionId == null || exportBusy.busy}
            >
              {exportBusy.busy ? "Exporting…" : `Export ${formatLabel}`}
            </Button>
          </div>

          <details className="disclosure">
            <summary>More options</summary>
            <div className="field-row">
              <Field label="Value mode" htmlFor="exp-mode">
                <select id="exp-mode" value={mode} onChange={(e) => setMode(e.target.value)}>
                  <option value="literal">Literal (A/B/C/D/Blank/Multi)</option>
                  <option value="binary">Binary (1/0 correct)</option>
                </select>
              </Field>
              <Field label="File format" htmlFor="exp-format">
                <select id="exp-format" value={format} onChange={(e) => setFormat(e.target.value)}>
                  <option value="csv">CSV</option>
                  <option value="xlsx">Excel</option>
                </select>
              </Field>
            </div>
          </details>
        </div>
      )}

      {scoresBusy.busy && (
        <div className="panel">
          <div className="skeleton skeleton-row" />
          <div className="skeleton skeleton-row" />
          <div className="skeleton skeleton-row" />
        </div>
      )}

      {scores && !scoresBusy.busy && (
        <div className="panel">
          <h2 style={{ marginBottom: 12 }}>
            {scores.session_name} <span className="muted">({scores.sheet_count} sheets)</span>
          </h2>

          <TableToolbar
            search={table.search}
            onSearchChange={table.setSearch}
            searchPlaceholder="Search roll number"
            showing={table.pagedRows.length}
            total={table.totalFiltered}
            onClear={() => {
              table.clearFilters();
              setMinPct("");
              setMaxPct("");
              setIssuesOnly(false);
            }}
            extra={
              <div className="row">
                <Field label="Min %" htmlFor="min-pct">
                  <input
                    id="min-pct"
                    type="number"
                    min={0}
                    max={100}
                    value={minPct}
                    onChange={(e) => setMinPct(e.target.value)}
                    style={{ width: 72 }}
                  />
                </Field>
                <Field label="Max %" htmlFor="max-pct">
                  <input
                    id="max-pct"
                    type="number"
                    min={0}
                    max={100}
                    value={maxPct}
                    onChange={(e) => setMaxPct(e.target.value)}
                    style={{ width: 72 }}
                  />
                </Field>
                <label className="muted" style={{ fontSize: 13, display: "flex", gap: 6 }}>
                  <input
                    type="checkbox"
                    checked={issuesOnly}
                    onChange={(e) => setIssuesOnly(e.target.checked)}
                  />
                  Blank/multi only
                </label>
              </div>
            }
          />

          {filteredResults.length === 0 ? (
            <EmptyState
              title="No rows match"
              description="Adjust filters or process more sheets for this scope."
            />
          ) : (
            <>
              <DataTable
                columns={columns}
                rows={table.pagedRows}
                rowKey={(r) => String(r.sheet_id ?? r.roll_no ?? "")}
                sortKey={table.sortKey}
                sortDir={table.sortDir}
                onSort={table.toggleSort}
              />
              <Pagination
                page={table.page}
                pageCount={table.pageCount}
                pageSize={table.pageSize}
                total={table.totalFiltered}
                onPageChange={table.setPage}
                onPageSizeChange={(size) => {
                  table.setPageSize(size);
                  table.setPage(1);
                }}
              />
            </>
          )}
        </div>
      )}
    </PageLayout>
  );
}
