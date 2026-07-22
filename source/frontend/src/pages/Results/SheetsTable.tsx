import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import Button from "../../components/Button";
import EmptyState from "../../components/EmptyState";
import ExamScopePicker from "../../components/ExamScopePicker";
import Lozenge from "../../components/Lozenge";
import SectionMessage from "../../components/SectionMessage";
import Spinner from "../../components/Spinner";
import DataTable, { type Column } from "../../components/table/DataTable";
import Pagination from "../../components/table/Pagination";
import TableToolbar, { type ToolbarFilter } from "../../components/table/TableToolbar";
import { useBusy } from "../../hooks/useBusy";
import { useTableState } from "../../hooks/useTableState";
import type { ExamScopeValue } from "../../hooks/useExamScope";

type Batch = { id: number; status: string };

type SheetRow = {
  id: number;
  roll_no: string | null;
  batch_id: number;
  status: string;
  percentage: number | null;
  secure_score: number | null;
  counts: { correct: number; wrong: number; blank: number; multi: number; total: number } | null;
  pending_verifications: number;
};

const STATUS_OPTIONS = [
  { value: "scored", label: "Scored" },
  { value: "pending_verification", label: "Pending verification" },
  { value: "excluded", label: "Excluded" },
  { value: "alignment_failed", label: "Alignment failed" },
];

type Props = {
  onReview?: () => void;
};

export default function SheetsTable({ onReview }: Props) {
  const loadBusy = useBusy();

  const [scope, setScope] = useState<ExamScopeValue>({
    programId: null,
    sessionId: null,
    batchId: null,
  });
  const [batches, setBatches] = useState<Batch[]>([]);
  const [sheets, setSheets] = useState<SheetRow[]>([]);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [batchFilter, setBatchFilter] = useState("");

  const sessionId = scope.sessionId;

  useEffect(() => {
    setBatches([]);
    setBatchFilter("");
    if (sessionId == null) return;
    api<{ batches: Batch[] }>(`/sessions/${sessionId}/batches`)
      .then((d) => setBatches(d.batches))
      .catch((e) => setError((e as Error).message));
  }, [sessionId]);

  const loadSheets = useCallback(async () => {
    if (sessionId == null) return;
    const params = new URLSearchParams();
    if (search.trim()) params.set("q", search.trim());
    if (statusFilter) params.set("status", statusFilter);
    if (batchFilter) params.set("batch_id", batchFilter);
    const qs = params.toString() ? `?${params}` : "";
    const data = await api<{ sheets: SheetRow[] }>(`/sessions/${sessionId}/sheets${qs}`);
    setSheets(data.sheets);
  }, [sessionId, search, statusFilter, batchFilter]);

  useEffect(() => {
    if (sessionId == null) {
      setSheets([]);
      return;
    }
    loadBusy.run(loadSheets).catch((e) => setError((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, search, statusFilter, batchFilter]);

  const flatSheets = sheets.map((s) => ({
    ...s,
    correct: s.counts?.correct ?? 0,
    wrong: s.counts?.wrong ?? 0,
    blank: s.counts?.blank ?? 0,
    multi: s.counts?.multi ?? 0,
    pct: s.percentage ?? 0,
    secure: s.secure_score ?? 0,
  }));

  const table = useTableState({
    rows: flatSheets,
    searchKeys: ["roll_no"],
    defaultSortKey: "roll_no",
  });

  const batchOptions = batches.map((b) => ({ value: String(b.id), label: `Batch #${b.id}` }));
  const toolbarFilters: ToolbarFilter[] = [
    { key: "status", label: "Status", options: STATUS_OPTIONS },
    { key: "batch_id", label: "Batch", options: batchOptions },
  ];

  const columns: Column<(typeof flatSheets)[0]>[] = [
    {
      key: "roll_no",
      label: "Roll",
      sortable: true,
      render: (s) => (
        <Link to={`/sheets/${s.id}`} state={{ from: "results" }}>
          {s.roll_no ?? "-"}
        </Link>
      ),
    },
    {
      key: "batch_id",
      label: "Batch",
      sortable: true,
      render: (s) => `#${s.batch_id}`,
    },
    { key: "correct", label: "Correct", sortable: true },
    { key: "wrong", label: "Wrong", sortable: true },
    { key: "blank", label: "Blank", sortable: true },
    { key: "multi", label: "Multi", sortable: true },
    { key: "pct", label: "%", sortable: true, render: (s) => s.percentage ?? "-" },
    { key: "secure", label: "Secure", sortable: true, render: (s) => s.secure_score ?? "-" },
    {
      key: "status",
      label: "Status",
      sortable: true,
      render: (s) => (
        <Lozenge
          appearance={
            s.status === "scored"
              ? "success"
              : s.status === "pending_verification"
                ? "warning"
                : "danger"
          }
        >
          {s.status.replace(/_/g, " ")}
        </Lozenge>
      ),
    },
    {
      key: "actions",
      label: "",
      render: (s) => (
        <div className="row">
          <Link to={`/sheets/${s.id}`} state={{ from: "results" }}>
            <Button variant="subtle">View</Button>
          </Link>
          {s.pending_verifications > 0 && onReview && (
            <Button variant="subtle" onClick={onReview}>
              Review
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <SectionMessage appearance="error">{error}</SectionMessage>

      <ExamScopePicker
        levels="program+session"
        value={scope}
        onChange={setScope}
        className="mb-6"
      />

      {loadBusy.busy && sessionId != null && <Spinner label="Loading sheets…" />}

      {sessionId != null && !loadBusy.busy && (
        <>
          <TableToolbar
            search={search}
            onSearchChange={setSearch}
            searchPlaceholder="Search roll"
            filters={toolbarFilters}
            filterValues={{ status: statusFilter, batch_id: batchFilter }}
            onFilterChange={(key, value) => {
              if (key === "status") setStatusFilter(value);
              if (key === "batch_id") setBatchFilter(value);
            }}
            onClear={() => {
              setSearch("");
              setStatusFilter("");
              setBatchFilter("");
            }}
            showing={table.pagedRows.length}
            total={sheets.length}
          />

          {sheets.length === 0 ? (
            <EmptyState
              title="No sheets found"
              description="Process scans for this session or adjust filters."
            />
          ) : (
            <>
              <DataTable
                columns={columns}
                rows={table.pagedRows}
                rowKey={(s) => s.id}
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
        </>
      )}
    </div>
  );
}
