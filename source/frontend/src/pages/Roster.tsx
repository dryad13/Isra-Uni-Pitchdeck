import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, upload } from "../lib/api";
import Button from "../components/Button";
import ConfirmDialog from "../components/ConfirmDialog";
import EmptyState from "../components/EmptyState";
import ExamScopePicker from "../components/ExamScopePicker";
import Field from "../components/Field";
import PageLayout from "../components/PageLayout";
import type { ExamScopeValue } from "../hooks/useExamScope";
import FileUpload from "../components/FileUpload";
import Lozenge from "../components/Lozenge";
import DataTable, { type Column } from "../components/table/DataTable";
import Pagination from "../components/table/Pagination";
import TableToolbar from "../components/table/TableToolbar";
import { useToast } from "../components/Toast";
import { useBusy } from "../hooks/useBusy";
import { useTableState } from "../hooks/useTableState";

type Program = { id: number; name: string };
type Session = { id: number; name: string };
type Student = {
  id: number;
  roll_no: string;
  name: string;
  class_section: string | null;
  batch_label: string | null;
};

type EditDraft = Partial<Pick<Student, "roll_no" | "name" | "class_section" | "batch_label">>;

type ImportCandidate = {
  roll_no: string;
  on_roster: boolean;
  sheet_count: number;
  last_batch_id: number;
};

export default function Roster() {
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const initBusy = useBusy();
  const uploadBusy = useBusy();
  const saveBusy = useBusy();
  const importBusy = useBusy();

  const [scope, setScope] = useState<ExamScopeValue>({
    programId: searchParams.get("program") ? Number(searchParams.get("program")) : null,
    sessionId: null,
    batchId: null,
  });
  const programId = scope.programId;
  const [programs, setPrograms] = useState<Program[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [importSessionId, setImportSessionId] = useState<number | null>(null);
  const [candidates, setCandidates] = useState<ImportCandidate[]>([]);
  const [selectedRolls, setSelectedRolls] = useState<Set<string>>(new Set());
  const [students, setStudents] = useState<Student[]>([]);
  const [error, setError] = useState("");
  const [confirmRoll, setConfirmRoll] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<EditDraft>({});

  const loadStudents = useCallback(
    async (pid: number, q: string, classSection: string, batchLabel: string) => {
      const params = new URLSearchParams();
      if (q.trim()) params.set("q", q.trim());
      if (classSection) params.set("class_section", classSection);
      if (batchLabel) params.set("batch_label", batchLabel);
      const qs = params.toString() ? `?${params}` : "";
      const data = await api<{ students: Student[] }>(`/programs/${pid}/students${qs}`);
      setStudents(data.students);
    },
    [],
  );

  useEffect(() => {
    const params = new URLSearchParams(searchParams);
    if (programId != null) params.set("program", String(programId));
    else params.delete("program");
    setSearchParams(params, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [programId]);

  useEffect(() => {
    initBusy
      .run(async () => {
        const d = await api<{ programs: Program[] }>("/programs");
        setPrograms(d.programs);
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  const table = useTableState<Student>({
    rows: students,
    searchKeys: ["roll_no", "name", "class_section", "batch_label"],
    defaultSortKey: "roll_no",
    serverSide: true,
  });

  useEffect(() => {
    if (programId == null) {
      setSessions([]);
      setImportSessionId(null);
      setCandidates([]);
      setSelectedRolls(new Set());
      setStudents([]);
      return;
    }
    api<{ sessions: Session[] }>(`/programs/${programId}`)
      .then((d) => {
        setSessions(d.sessions);
        setImportSessionId(d.sessions[0]?.id ?? null);
      })
      .catch((e) => setError((e as Error).message));
    loadStudents(
      programId,
      table.search,
      table.filters.class_section ?? "",
      table.filters.batch_label ?? "",
    ).catch((e) => setError((e as Error).message));
  }, [programId, table.search, table.filters, loadStudents]);

  const classOptions = useMemo(() => {
    const set = new Set(students.map((s) => s.class_section).filter(Boolean) as string[]);
    return [...set].sort().map((v) => ({ value: v, label: v }));
  }, [students]);

  const batchOptions = useMemo(() => {
    const set = new Set(students.map((s) => s.batch_label).filter(Boolean) as string[]);
    return [...set].sort().map((v) => ({ value: v, label: v }));
  }, [students]);

  const uploadRoster = (files: FileList | null) => {
    if (programId == null || !files?.length) return;
    uploadBusy
      .run(async () => {
        setError("");
        const form = new FormData();
        form.append("file", files[0]);
        const result = await upload<{ created: number; updated: number }>(
          `/programs/${programId}/students/upload`,
          form,
        );
        toast.success(`Roster uploaded (${result.created} added, ${result.updated} updated).`);
        await loadStudents(
          programId,
          table.search,
          table.filters.class_section ?? "",
          table.filters.batch_label ?? "",
        );
      })
      .catch((e) => setError((e as Error).message));
  };

  const previewImport = () => {
    if (programId == null || importSessionId == null) return;
    importBusy
      .run(async () => {
        setError("");
        const data = await api<{ candidates: ImportCandidate[] }>(
          `/programs/${programId}/roster/candidates?session_id=${importSessionId}`,
        );
        setCandidates(data.candidates);
        setSelectedRolls(
          new Set(data.candidates.filter((c) => !c.on_roster).map((c) => c.roll_no)),
        );
      })
      .catch((e) => setError((e as Error).message));
  };

  const importRolls = (rolls: string[] | null) => {
    if (programId == null || importSessionId == null) return;
    importBusy
      .run(async () => {
        setError("");
        const result = await api<{ created: number; skipped: number }>(
          `/programs/${programId}/roster/import-from-session`,
          {
            method: "POST",
            body: JSON.stringify({ session_id: importSessionId, rolls }),
          },
        );
        toast.success(`Imported ${result.created} roll(s) (${result.skipped} already on roster).`);
        setCandidates([]);
        setSelectedRolls(new Set());
        await loadStudents(
          programId,
          table.search,
          table.filters.class_section ?? "",
          table.filters.batch_label ?? "",
        );
      })
      .catch((e) => setError((e as Error).message));
  };

  const toggleRoll = (roll: string) => {
    setSelectedRolls((prev) => {
      const next = new Set(prev);
      if (next.has(roll)) next.delete(roll);
      else next.add(roll);
      return next;
    });
  };

  const deleteStudent = async () => {
    if (programId == null || !confirmRoll) return;
    setError("");
    try {
      await api(`/programs/${programId}/students/${encodeURIComponent(confirmRoll)}`, {
        method: "DELETE",
      });
      toast.success(`Removed roll ${confirmRoll}.`);
      setConfirmRoll(null);
      await loadStudents(
        programId,
        table.search,
        table.filters.class_section ?? "",
        table.filters.batch_label ?? "",
      );
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const startEdit = (s: Student) => {
    setEditingId(s.id);
    setDraft({
      roll_no: s.roll_no,
      name: s.name,
      class_section: s.class_section ?? "",
      batch_label: s.batch_label ?? "",
    });
  };

  const saveEdit = (original: Student) => {
    if (programId == null) return;
    saveBusy
      .run(async () => {
        setError("");
        await api(`/programs/${programId}/students`, {
          method: "POST",
          body: JSON.stringify({
            entries: [
              {
                roll_no: draft.roll_no ?? original.roll_no,
                name: draft.name ?? original.name,
                class_section: draft.class_section || null,
                batch_label: draft.batch_label || null,
              },
            ],
          }),
        });
        toast.success("Student saved.");
        setEditingId(null);
        await loadStudents(
          programId,
          table.search,
          table.filters.class_section ?? "",
          table.filters.batch_label ?? "",
        );
      })
      .catch((e) => setError((e as Error).message));
  };

  const columns: Column<Student>[] = [
    {
      key: "roll_no",
      label: "Roll",
      sortable: true,
      render: (s) =>
        editingId === s.id ? (
          <input
            className="inline-edit-cell"
            value={draft.roll_no ?? ""}
            onChange={(e) => setDraft({ ...draft, roll_no: e.target.value })}
          />
        ) : (
          s.roll_no
        ),
    },
    {
      key: "name",
      label: "Name",
      sortable: true,
      render: (s) =>
        editingId === s.id ? (
          <input
            className="inline-edit-cell"
            value={draft.name ?? ""}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          />
        ) : (
          s.name
        ),
    },
    {
      key: "class_section",
      label: "Class",
      sortable: true,
      render: (s) =>
        editingId === s.id ? (
          <input
            className="inline-edit-cell"
            value={draft.class_section ?? ""}
            onChange={(e) => setDraft({ ...draft, class_section: e.target.value })}
          />
        ) : (
          s.class_section ?? "-"
        ),
    },
    {
      key: "batch_label",
      label: "Batch",
      sortable: true,
      render: (s) =>
        editingId === s.id ? (
          <input
            className="inline-edit-cell"
            value={draft.batch_label ?? ""}
            onChange={(e) => setDraft({ ...draft, batch_label: e.target.value })}
          />
        ) : (
          s.batch_label ?? "-"
        ),
    },
    {
      key: "actions",
      label: "",
      render: (s) =>
        editingId === s.id ? (
          <div className="row">
            <Button variant="primary" onClick={() => saveEdit(s)} disabled={saveBusy.busy}>
              Save
            </Button>
            <Button variant="subtle" onClick={() => setEditingId(null)}>
              Cancel
            </Button>
          </div>
        ) : (
          <div className="row">
            <Button variant="link" onClick={() => startEdit(s)}>
              edit
            </Button>
            <Button variant="danger-link" onClick={() => setConfirmRoll(s.roll_no)}>
              delete
            </Button>
          </div>
        ),
    },
  ];

  const clientTable = useTableState<Student>({
    rows: students,
    searchKeys: ["roll_no", "name"],
    defaultSortKey: "roll_no",
  });

  return (
    <PageLayout
      title="Student roster"
      subtitle="Upload a CSV or Excel roster per exam program. Scanned roll numbers are checked against this list during processing."
      error={error}
      loading={initBusy.busy}
      loadingLabel="Loading exams…"
      empty={
        !initBusy.busy && programs.length === 0
          ? {
              title: "No exams yet",
              description: "Create an exam on the Run exam page, then return here to upload a roster.",
              action: (
                <Link to="/">
                  <Button variant="default">Go to Run exam</Button>
                </Link>
              ),
            }
          : null
      }
    >
      {programs.length > 0 && (
        <div className="panel">
          <ExamScopePicker
            levels="program"
            value={scope}
            onChange={setScope}
            className="mb-5"
          />

          {programId != null && (
            <>
              <TableToolbar
                search={table.search}
                onSearchChange={table.setSearch}
                searchPlaceholder="Roll or name"
                filters={[
                  { key: "class_section", label: "Class", options: classOptions },
                  { key: "batch_label", label: "Batch", options: batchOptions },
                ]}
                filterValues={table.filters}
                onFilterChange={table.setFilter}
                onClear={table.clearFilters}
                showing={clientTable.pagedRows.length}
                total={students.length}
              />

              <Field
                label="Upload roster"
                hint="CSV or Excel with roll_no and name columns"
                htmlFor="roster-file"
              >
                <FileUpload
                  id="roster-file"
                  accept=".csv,.xlsx,.xls"
                  busy={uploadBusy.busy}
                  onFile={uploadRoster}
                  hint="CSV or Excel roster file"
                />
              </Field>

              <div className="panel-subsection" style={{ marginTop: 24 }}>
                <h3>Import from session</h3>
                <p className="muted" style={{ marginBottom: 12 }}>
                  Add roll numbers detected in a processed scan session to the roster.
                </p>
                <div className="field-row">
                  <Field label="Session" htmlFor="import-session">
                    <select
                      id="import-session"
                      value={importSessionId ?? ""}
                      onChange={(e) => {
                        setImportSessionId(e.target.value ? Number(e.target.value) : null);
                        setCandidates([]);
                        setSelectedRolls(new Set());
                      }}
                    >
                      <option value="">Select session</option>
                      {sessions.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Button
                    variant="default"
                    onClick={previewImport}
                    disabled={importSessionId == null || importBusy.busy}
                  >
                    Preview
                  </Button>
                </div>

                {candidates.length > 0 && (
                  <>
                    <table className="sub-table" style={{ marginTop: 12 }}>
                      <thead>
                        <tr>
                          <th />
                          <th>Roll</th>
                          <th>On roster</th>
                          <th>Sheets</th>
                        </tr>
                      </thead>
                      <tbody>
                        {candidates.map((c) => (
                          <tr key={c.roll_no}>
                            <td>
                              <input
                                type="checkbox"
                                checked={selectedRolls.has(c.roll_no)}
                                disabled={c.on_roster}
                                onChange={() => toggleRoll(c.roll_no)}
                              />
                            </td>
                            <td>{c.roll_no}</td>
                            <td>
                              <Lozenge appearance={c.on_roster ? "success" : "warning"}>
                                {c.on_roster ? "On roster" : "New"}
                              </Lozenge>
                            </td>
                            <td>{c.sheet_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <div className="row" style={{ marginTop: 12 }}>
                      <Button
                        variant="primary"
                        onClick={() => importRolls([...selectedRolls])}
                        disabled={selectedRolls.size === 0 || importBusy.busy}
                      >
                        Import selected
                      </Button>
                      <Button
                        variant="subtle"
                        onClick={() => importRolls(null)}
                        disabled={importBusy.busy}
                      >
                        Import all new
                      </Button>
                    </div>
                  </>
                )}
              </div>

              {students.length === 0 ? (
                <EmptyState
                  title="No students on roster"
                  description="Upload a roster file or adjust your search filters."
                />
              ) : (
                <>
                  <DataTable
                    columns={columns}
                    rows={clientTable.pagedRows}
                    rowKey={(s) => s.id}
                    sortKey={clientTable.sortKey}
                    sortDir={clientTable.sortDir}
                    onSort={clientTable.toggleSort}
                  />
                  <Pagination
                    page={clientTable.page}
                    pageCount={clientTable.pageCount}
                    pageSize={clientTable.pageSize}
                    total={clientTable.totalFiltered}
                    onPageChange={clientTable.setPage}
                    onPageSizeChange={(size) => {
                      clientTable.setPageSize(size);
                      clientTable.setPage(1);
                    }}
                  />
                </>
              )}
            </>
          )}
        </div>
      )}

      <ConfirmDialog
        open={confirmRoll != null}
        title="Remove student?"
        message={`Remove roll ${confirmRoll} from the roster?`}
        confirmLabel="Delete"
        danger
        onConfirm={deleteStudent}
        onCancel={() => setConfirmRoll(null)}
      />
    </PageLayout>
  );
}
