import { useEffect, useRef, useState } from "react";
import type { EnvironmentFilter, FilterState } from "../types/filters";

export interface FiltersBarProps {
  onFilter: (filters: FilterState) => void;
}

const DEFAULT: FilterState = {
  dateFrom: "",
  dateTo: "",
  riskThreshold: 0.5,
  typology: "",
  environment: "all",
  search: "",
};

const TYPOLOGY_OPTIONS = [
  { value: "", label: "All typologies" },
  { value: "layering", label: "Layering" },
  { value: "structuring", label: "Structuring" },
  { value: "mixer", label: "Mixer / tumbler" },
  { value: "peel_chain", label: "Peel chain" },
  { value: "exchange_hop", label: "Exchange hop" },
];

const ENV_OPTIONS: { value: EnvironmentFilter; label: string }[] = [
  { value: "all", label: "All environments" },
  { value: "traditional", label: "Traditional" },
  { value: "blockchain", label: "Blockchain" },
  { value: "hybrid", label: "Hybrid" },
  { value: "ai_enabled", label: "AI-enabled" },
];

export default function FiltersBar({ onFilter }: FiltersBarProps) {
  const [filters, setFilters] = useState<FilterState>(DEFAULT);
  const onFilterRef = useRef(onFilter);
  onFilterRef.current = onFilter;

  useEffect(() => {
    onFilterRef.current(filters);
  }, [filters]);

  function patch<K extends keyof FilterState>(key: K, value: FilterState[K]) {
    setFilters((f) => ({ ...f, [key]: value }));
  }

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-xl border border-gray-800 bg-gray-900 p-4 text-gray-100">
      <label className="flex min-w-[140px] flex-1 flex-col gap-1 text-xs text-gray-400">
        From
        <input
          type="date"
          value={filters.dateFrom}
          onChange={(e) => patch("dateFrom", e.target.value)}
          className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-100 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/30"
        />
      </label>
      <label className="flex min-w-[140px] flex-1 flex-col gap-1 text-xs text-gray-400">
        To
        <input
          type="date"
          value={filters.dateTo}
          onChange={(e) => patch("dateTo", e.target.value)}
          className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-100 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/30"
        />
      </label>
      <label className="flex min-w-[180px] flex-[1.2] flex-col gap-1 text-xs text-gray-400">
        Risk threshold ({filters.riskThreshold.toFixed(2)})
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={filters.riskThreshold}
          onChange={(e) =>
            patch("riskThreshold", Number.parseFloat(e.target.value))
          }
          className="h-2 w-full cursor-pointer accent-blue-500"
        />
      </label>
      <label className="flex min-w-[160px] flex-1 flex-col gap-1 text-xs text-gray-400">
        Typology
        <select
          value={filters.typology}
          onChange={(e) => patch("typology", e.target.value)}
          className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-100 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/30"
        >
          {TYPOLOGY_OPTIONS.map((o) => (
            <option key={o.value || "all"} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex min-w-[180px] flex-1 flex-col gap-1 text-xs text-gray-400">
        Environment
        <select
          value={filters.environment}
          onChange={(e) =>
            patch("environment", e.target.value as EnvironmentFilter)
          }
          className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-100 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/30"
        >
          {ENV_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex min-w-[200px] flex-[1.5] flex-col gap-1 text-xs text-gray-400">
        Search
        <input
          type="search"
          placeholder="TX ID, wallet, hash…"
          value={filters.search}
          onChange={(e) => patch("search", e.target.value)}
          className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2 text-sm text-gray-100 placeholder:text-gray-600 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/30"
        />
      </label>
    </div>
  );
}
