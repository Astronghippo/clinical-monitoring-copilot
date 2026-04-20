"use client";
import { useState } from "react";
import { Search, Sparkles, X } from "lucide-react";
import { api } from "@/lib/api";

export interface NLFilters {
  analyzer: string | null;
  severity: string[] | null;
  status: string[] | null;
  search_text: string | null;
}

interface Props {
  analysisId: number;
  onFiltersApplied: (filters: NLFilters) => void;
}

const EXAMPLE_QUERIES = [
  "Show critical open findings",
  "Out-of-range labs",
  "Eligibility violations",
];

export function NLFilterBar({ analysisId, onFiltersApplied }: Props) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applied, setApplied] = useState(false);

  async function submit() {
    if (!query.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const filters = await api.nlFilter(analysisId, query);
      onFiltersApplied(filters);
      setApplied(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function clear() {
    setQuery("");
    setApplied(false);
    setError(null);
    onFiltersApplied({ analyzer: null, severity: null, status: null, search_text: null });
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") submit();
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search
            size={14}
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (applied) setApplied(false);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search in plain English, e.g. 'critical open findings'"
            className="w-full rounded border border-slate-300 py-2 pl-8 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-violet-400"
          />
        </div>
        <button
          type="button"
          onClick={submit}
          disabled={loading || !query.trim()}
          className="inline-flex items-center gap-2 rounded border border-violet-200 bg-violet-50 px-3 py-2 text-sm font-medium text-violet-800 hover:bg-violet-100 disabled:opacity-50"
        >
          <Sparkles size={13} />
          {loading ? "Asking…" : "Ask Claude"}
        </button>
        {applied && (
          <button
            type="button"
            onClick={clear}
            aria-label="Clear filters"
            className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            <X size={13} />
            Clear
          </button>
        )}
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      {!applied && !loading && (
        <div className="flex flex-wrap gap-1.5">
          {EXAMPLE_QUERIES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setQuery(ex)}
              className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs text-slate-500 hover:bg-slate-100"
            >
              {ex}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
