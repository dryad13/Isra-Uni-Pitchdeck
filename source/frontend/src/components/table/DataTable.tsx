import { Fragment } from "react";
import EmptyState from "../EmptyState";

export type Column<T> = {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (row: T) => React.ReactNode;
};

type Props<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  sortKey?: string | null;
  sortDir?: "asc" | "desc";
  onSort?: (key: string) => void;
  onRowClick?: (row: T) => void;
  expandedRowKey?: string | number | null;
  renderExpanded?: (row: T) => React.ReactNode;
  emptyTitle?: string;
  emptyDescription?: string;
  filteredEmptyTitle?: string;
};

export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  sortKey,
  sortDir,
  onSort,
  onRowClick,
  expandedRowKey,
  renderExpanded,
  emptyDescription,
  filteredEmptyTitle = "No rows match your filters",
}: Props<T>) {
  if (rows.length === 0) {
    return (
      <EmptyState
        title={filteredEmptyTitle}
        description={emptyDescription ?? "Try adjusting search or filters."}
      />
    );
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={col.sortable ? "sortable-th" : undefined}
                onClick={col.sortable && onSort ? () => onSort(col.key) : undefined}
                aria-sort={
                  col.sortable && sortKey === col.key
                    ? sortDir === "asc"
                      ? "ascending"
                      : "descending"
                    : undefined
                }
              >
                {col.label}
                {col.sortable && sortKey === col.key && (
                  <span className="sort-indicator">{sortDir === "asc" ? " ▲" : " ▼"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const key = rowKey(row);
            const expanded = expandedRowKey === key;
            return (
              <Fragment key={key}>
                <tr
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  style={onRowClick ? { cursor: "pointer" } : undefined}
                  className={expanded ? "selected" : undefined}
                >
                  {columns.map((col) => (
                    <td key={col.key}>
                      {col.render
                        ? col.render(row)
                        : String((row as Record<string, unknown>)[col.key] ?? "-")}
                    </td>
                  ))}
                </tr>
                {expanded && renderExpanded && (
                  <tr className="expanded-row">
                    <td colSpan={columns.length}>{renderExpanded(row)}</td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
