import { useCallback, useMemo, useState } from "react";

export type SortDir = "asc" | "desc";

export type TableFilter = {
  key: string;
  value: string;
};

export type UseTableStateOptions<T> = {
  rows: T[];
  searchKeys?: (keyof T | ((row: T) => string))[];
  defaultSortKey?: string;
  defaultPageSize?: number;
  serverSide?: boolean;
};

export function filterRows<T>(
  rows: T[],
  search: string,
  searchKeys: (keyof T | ((row: T) => string))[],
): T[] {
  const term = search.trim().toLowerCase();
  if (!term) return rows;
  return rows.filter((row) =>
    searchKeys.some((key) => {
      const val = typeof key === "function" ? key(row) : String(row[key] ?? "");
      return val.toLowerCase().includes(term);
    }),
  );
}

export function sortRows<T extends Record<string, unknown>>(
  rows: T[],
  sortKey: string | null,
  sortDir: SortDir,
): T[] {
  if (!sortKey) return rows;
  const sorted = [...rows].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === "number" && typeof bv === "number") return av - bv;
    return String(av).localeCompare(String(bv), undefined, { numeric: true });
  });
  return sortDir === "desc" ? sorted.reverse() : sorted;
}

export function paginateRows<T>(rows: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return rows.slice(start, start + pageSize);
}

export function useTableState<T extends Record<string, unknown>>({
  rows,
  searchKeys = [],
  defaultSortKey,
  defaultPageSize = 25,
  serverSide = false,
}: UseTableStateOptions<T>) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(defaultSortKey ?? null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize);

  const setFilter = useCallback((key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  }, []);

  const clearFilters = useCallback(() => {
    setSearch("");
    setFilters({});
    setPage(1);
  }, []);

  const toggleSort = useCallback((key: string) => {
    setSortKey((prev) => {
      if (prev === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        return key;
      }
      setSortDir("asc");
      return key;
    });
    setPage(1);
  }, []);

  const filtered = useMemo(() => {
    if (serverSide) return rows;
    let result = filterRows(rows, search, searchKeys);
    for (const [key, value] of Object.entries(filters)) {
      if (!value) continue;
      result = result.filter((row) => String(row[key] ?? "") === value);
    }
    return sortRows(result, sortKey, sortDir);
  }, [rows, search, searchKeys, filters, sortKey, sortDir, serverSide]);

  const totalFiltered = filtered.length;
  const pageCount = Math.max(1, Math.ceil(totalFiltered / pageSize));
  const safePage = Math.min(page, pageCount);

  const paged = useMemo(() => {
    if (serverSide) return rows;
    return paginateRows(filtered, safePage, pageSize);
  }, [filtered, safePage, pageSize, rows, serverSide]);

  return {
    search,
    setSearch,
    sortKey,
    sortDir,
    toggleSort,
    filters,
    setFilter,
    clearFilters,
    page: safePage,
    setPage,
    pageSize,
    setPageSize,
    pageCount,
    totalFiltered,
    totalRows: rows.length,
    pagedRows: paged,
  };
}
