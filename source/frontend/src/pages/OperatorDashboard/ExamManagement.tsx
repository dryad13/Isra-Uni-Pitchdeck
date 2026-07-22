import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../../lib/api";
import Button from "../../components/Button";
import ConfirmDialog from "../../components/ConfirmDialog";
import EmptyState from "../../components/EmptyState";
import Lozenge from "../../components/Lozenge";
import SectionMessage from "../../components/SectionMessage";
import Spinner from "../../components/Spinner";
import DataTable, { type Column } from "../../components/table/DataTable";
import Pagination from "../../components/table/Pagination";
import TableToolbar from "../../components/table/TableToolbar";
import { useToast } from "../../components/Toast";
import { useBusy } from "../../hooks/useBusy";
import { useTableState } from "../../hooks/useTableState";

type Program = {
  id: number;
  name: string;
  key_coverage_end: number | null;
  planned_max_questions: number | null;
  roster_sync_mode?: string;
  session_count?: number;
  student_count?: number;
  sheet_count?: number;
};

type SessionRow = {
  id: number;
  name: string;
  global_q_start: number;
  global_q_end: number;
  key_complete: boolean;
  key_filled?: number;
  key_total?: number;
};

export default function ExamManagement() {
  const toast = useToast();
  const navigate = useNavigate();
  const loadBusy = useBusy();
  const deleteBusy = useBusy();

  const [programs, setPrograms] = useState<Program[]>([]);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [keyFilter, setKeyFilter] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [confirmId, setConfirmId] = useState<number | null>(null);

  const loadPrograms = useCallback(async (q: string) => {
    const qs = new URLSearchParams({ include: "stats" });
    if (q.trim()) qs.set("q", q.trim());
    const data = await api<{ programs: Program[] }>(`/programs?${qs}`);
    setPrograms(data.programs);
  }, []);

  useEffect(() => {
    loadBusy.run(() => loadPrograms(search)).catch((e) => setError((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const filtered = programs.filter((p) => {
    const end = p.key_coverage_end ?? 0;
    if (keyFilter === "ready") {
      const planned = p.planned_max_questions;
      return planned ? end >= planned : end > 0;
    }
    if (keyFilter === "partial") return end > 0;
    if (keyFilter === "empty") return end === 0;
    return true;
  });

  const table = useTableState<Program>({
    rows: filtered,
    searchKeys: ["name"],
    defaultSortKey: "name",
    serverSide: true,
  });

  const expandProgram = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    try {
      const data = await api<{ sessions: SessionRow[] }>(`/programs/${id}`);
      setSessions(data.sessions);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const setRosterSyncMode = async (programId: number, mode: "auto" | "manual") => {
    try {
      await api(`/programs/${programId}`, {
        method: "PATCH",
        body: JSON.stringify({ roster_sync_mode: mode }),
      });
      toast.success(`Roster sync set to ${mode}.`);
      await loadPrograms(search);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const deleteProgram = async () => {
    if (confirmId == null) return;
    try {
      await deleteBusy.run(() =>
        api(`/programs/${confirmId}`, { method: "DELETE" }),
      );
      toast.success("Exam deleted.");
      setConfirmId(null);
      if (expandedId === confirmId) setExpandedId(null);
      await loadPrograms(search);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const openWorkflow = (programId: number, sessionId?: number) => {
    const params = new URLSearchParams({ program: String(programId) });
    if (sessionId != null) params.set("session", String(sessionId));
    navigate(`/?${params}`);
  };

  const columns: Column<Program>[] = [
    {
      key: "name",
      label: "Exam",
      sortable: true,
      render: (p) => (
        <button type="button" className="btn-link" onClick={() => openWorkflow(p.id)}>
          {p.name}
        </button>
      ),
    },
    {
      key: "session_count",
      label: "Sessions",
      sortable: true,
      render: (p) => p.session_count ?? 0,
    },
    {
      key: "student_count",
      label: "Roster",
      sortable: true,
      render: (p) => (
        <Link to={`/roster?program=${p.id}`}>{p.student_count ?? 0}</Link>
      ),
    },
    {
      key: "sheet_count",
      label: "Sheets",
      sortable: true,
      render: (p) => p.sheet_count ?? 0,
    },
    {
      key: "key_coverage_end",
      label: "Key coverage",
      sortable: true,
      render: (p) => (
        <Lozenge appearance={(p.key_coverage_end ?? 0) > 0 ? "success" : "warning"}>
          Q{p.key_coverage_end ?? 0}
        </Lozenge>
      ),
    },
    {
      key: "roster_sync_mode",
      label: "Roster sync",
      render: (p) => (
        <select
          className="inline-select"
          value={p.roster_sync_mode ?? "auto"}
          title="Auto adds rolls from scans; Manual sends unknown rolls to Results queue"
          onChange={(e) =>
            setRosterSyncMode(p.id, e.target.value as "auto" | "manual")
          }
        >
          <option value="auto">Auto</option>
          <option value="manual">Manual</option>
        </select>
      ),
    },
    {
      key: "actions",
      label: "",
      render: (p) => (
        <div className="row">
          <Button variant="subtle" onClick={() => expandProgram(p.id)}>
            {expandedId === p.id ? "Collapse" : "Sessions"}
          </Button>
          <Button variant="default" onClick={() => openWorkflow(p.id)}>
            Open
          </Button>
          <Button variant="danger-link" onClick={() => setConfirmId(p.id)}>
            delete
          </Button>
        </div>
      ),
    },
  ];

  const confirmProgram = programs.find((p) => p.id === confirmId);

  return (
    <>
      <SectionMessage appearance="error">{error}</SectionMessage>

      {loadBusy.busy && <Spinner label="Loading exams…" />}

      {!loadBusy.busy && programs.length === 0 && (
        <EmptyState
          title="No exams yet"
          description="Create your first exam in Run workflow mode."
        />
      )}

      {programs.length > 0 && (
        <div className="panel">
          <TableToolbar
            search={search}
            onSearchChange={setSearch}
            searchPlaceholder="Search exam name"
            filters={[
              {
                key: "key",
                label: "Key status",
                options: [
                  { value: "ready", label: "Key complete" },
                  { value: "partial", label: "Partial key" },
                  { value: "empty", label: "No key" },
                ],
              },
            ]}
            filterValues={{ key: keyFilter }}
            onFilterChange={(_, value) => setKeyFilter(value)}
            onClear={() => {
              setSearch("");
              setKeyFilter("");
            }}
            showing={table.pagedRows.length}
            total={filtered.length}
          />

          <DataTable
            columns={columns}
            rows={table.pagedRows}
            rowKey={(p) => p.id}
            sortKey={table.sortKey}
            sortDir={table.sortDir}
            onSort={table.toggleSort}
            expandedRowKey={expandedId}
            renderExpanded={() =>
              sessions.length === 0 ? (
                <p className="muted">No sessions for this exam.</p>
              ) : (
                <table className="sub-table">
                  <thead>
                    <tr>
                      <th>Session</th>
                      <th>Range</th>
                      <th>Key</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map((s) => (
                      <tr key={s.id}>
                        <td>{s.name}</td>
                        <td>
                          Q{s.global_q_start}&ndash;Q{s.global_q_end}
                        </td>
                        <td>
                          <Lozenge appearance={s.key_complete ? "success" : "warning"}>
                            {s.key_filled ?? 0}/{s.key_total ?? 0}
                          </Lozenge>
                        </td>
                        <td>
                          <Button
                            variant="subtle"
                            onClick={() => openWorkflow(expandedId!, s.id)}
                          >
                            Open
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
            }
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
        </div>
      )}

      <ConfirmDialog
        open={confirmId != null}
        title="Delete exam?"
        message={
          confirmProgram
            ? `"${confirmProgram.name}" and all sessions, keys, and roster entries will be removed.`
            : ""
        }
        confirmLabel="Delete"
        danger
        busy={deleteBusy.busy}
        onConfirm={deleteProgram}
        onCancel={() => setConfirmId(null)}
      />
    </>
  );
}
