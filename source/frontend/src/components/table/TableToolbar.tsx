import { useEffect, useState } from "react";
import Button from "../Button";
import Field from "../Field";

export type ToolbarFilter = {
  key: string;
  label: string;
  options: { value: string; label: string }[];
};

type Props = {
  search: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  filters?: ToolbarFilter[];
  filterValues?: Record<string, string>;
  onFilterChange?: (key: string, value: string) => void;
  onClear?: () => void;
  showing?: number;
  total?: number;
  extra?: React.ReactNode;
};

export default function TableToolbar({
  search,
  onSearchChange,
  searchPlaceholder = "Search…",
  filters = [],
  filterValues = {},
  onFilterChange,
  onClear,
  showing,
  total,
  extra,
}: Props) {
  const [draft, setDraft] = useState(search);

  useEffect(() => {
    setDraft(search);
  }, [search]);

  useEffect(() => {
    const id = window.setTimeout(() => onSearchChange(draft), 300);
    return () => window.clearTimeout(id);
  }, [draft, onSearchChange]);

  const hasActive =
    draft.trim() !== "" || filters.some((f) => filterValues[f.key]);

  return (
    <div className="table-toolbar">
      <div className="table-toolbar-main">
        <Field label="Search" htmlFor="table-search">
          <input
            id="table-search"
            value={draft}
            placeholder={searchPlaceholder}
            onChange={(e) => setDraft(e.target.value)}
          />
        </Field>
        {filters.map((f) => (
          <Field key={f.key} label={f.label} htmlFor={`filter-${f.key}`}>
            <select
              id={`filter-${f.key}`}
              value={filterValues[f.key] ?? ""}
              onChange={(e) => onFilterChange?.(f.key, e.target.value)}
            >
              <option value="">All</option>
              {f.options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </Field>
        ))}
        {hasActive && onClear && (
          <Button variant="subtle" onClick={onClear}>
            Clear filters
          </Button>
        )}
      </div>
      <div className="table-toolbar-meta">
        {showing != null && total != null && (
          <span className="muted">
            Showing {showing} of {total}
          </span>
        )}
        {extra}
      </div>
    </div>
  );
}
