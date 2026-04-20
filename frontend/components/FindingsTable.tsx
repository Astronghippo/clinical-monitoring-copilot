"use client";
import React, { useEffect, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { clsx } from "clsx";
import type { Finding, FindingStatus, Severity, AnalyzerKind } from "@/lib/types";
import { FindingStatusBadge } from "./FindingStatusBadge";
import { Tooltip } from "./Tooltip";

const SEV_STYLES: Record<Severity, string> = {
  critical: "bg-red-100 text-red-800",
  major: "bg-amber-100 text-amber-800",
  minor: "bg-slate-100 text-slate-700",
};

const ANALYZER_LABEL: Record<AnalyzerKind, string> = {
  visit_windows: "Visit window",
  completeness: "Completeness",
  eligibility: "Eligibility",
  plausibility: "Plausibility",
};

const VIRTUALIZE_THRESHOLD = 20;
const ROW_HEIGHT = 44;
const CONTAINER_HEIGHT = 600;

interface Props {
  findings: Finding[];
  onSelect?: (f: Finding) => void;
  onStatusChange?: (id: number, next: FindingStatus) => Promise<void>;
  selectedIds?: Set<number>;
  onToggleSelected?: (id: number) => void;
  onSubjectClick?: (subjectId: string) => void;
  analysisId?: number;
  highlightedIndex?: number;
}

function FindingRow({
  f,
  onSelect,
  onStatusChange,
  selectedIds,
  onToggleSelected,
  onSubjectClick,
  analysisId,
  copiedId,
  onCopyLink,
  style,
  highlighted,
}: {
  f: Finding;
  onSelect?: (f: Finding) => void;
  onStatusChange?: (id: number, next: FindingStatus) => Promise<void>;
  selectedIds?: Set<number>;
  onToggleSelected?: (id: number) => void;
  onSubjectClick?: (subjectId: string) => void;
  analysisId?: number;
  copiedId: number | null;
  onCopyLink: (e: React.MouseEvent, id: number) => void;
  style?: React.CSSProperties;
  highlighted?: boolean;
}) {
  return (
    <div
      data-testid={`finding-row-${f.id}`}
      style={style}
      className={clsx(
        "flex items-center cursor-pointer border-b border-slate-100 hover:bg-slate-50 text-sm dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700",
        highlighted && "bg-blue-50 outline outline-2 outline-blue-400",
      )}
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(f)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect?.(f);
        }
      }}
    >
      {onToggleSelected && (
        <div
          className="px-3 py-2 w-10 flex-shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          <input
            type="checkbox"
            checked={selectedIds?.has(f.id) ?? false}
            onChange={() => onToggleSelected(f.id)}
            className="rounded border-slate-300"
          />
        </div>
      )}
      <div className="px-3 py-2 w-24 flex-shrink-0">
        <Tooltip text="Severity level of this finding (Critical, High, Medium, Low)">
          <span
            className={clsx(
              "rounded px-2 py-0.5 text-xs font-medium",
              SEV_STYLES[f.severity],
            )}
          >
            {f.severity}
          </span>
        </Tooltip>
      </div>
      <div className="hidden sm:block px-3 py-2 w-32 flex-shrink-0 text-slate-600">
        {ANALYZER_LABEL[f.analyzer] ?? f.analyzer}
      </div>
      <div className="px-3 py-2 w-28 flex-shrink-0 font-mono">
        {onSubjectClick ? (
          <button
            type="button"
            className="text-blue-600 hover:underline font-mono"
            onClick={(e) => {
              e.stopPropagation();
              onSubjectClick(f.subject_id);
            }}
          >
            {f.subject_id}
          </button>
        ) : (
          f.subject_id
        )}
      </div>
      <div className="px-3 py-2 flex-1 min-w-0">{f.summary}</div>
      <div className="hidden sm:block px-3 py-2 w-20 flex-shrink-0 text-slate-500">
        <Tooltip text="AI confidence score (0–100%). Higher is more certain.">
          <span>{(f.confidence * 100).toFixed(0)}%</span>
        </Tooltip>
      </div>
      {onStatusChange && (
        <div
          className="px-3 py-2 w-28 flex-shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          <FindingStatusBadge
            value={f.status}
            onChange={(next) => onStatusChange(f.id, next)}
          />
        </div>
      )}
      {analysisId !== undefined && (
        <div
          className="px-3 py-2 w-10 flex-shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            aria-label="Copy link to finding"
            className="text-slate-400 hover:text-slate-700 text-xs px-1"
            onClick={(e) => onCopyLink(e, f.id)}
          >
            {copiedId === f.id ? "✓" : "🔗"}
          </button>
        </div>
      )}
    </div>
  );
}

function TableHeader({
  onToggleSelected,
  onStatusChange,
  analysisId,
}: {
  onToggleSelected?: (id: number) => void;
  onStatusChange?: (id: number, next: FindingStatus) => Promise<void>;
  analysisId?: number;
}) {
  return (
    <div className="flex items-center bg-slate-50 text-left text-slate-600 text-sm font-medium border-b border-slate-200 dark:bg-gray-900 dark:text-gray-300 dark:border-gray-700">
      {onToggleSelected && <div className="px-3 py-2 w-10 flex-shrink-0"><span aria-label="Select">✓</span></div>}
      <div className="px-3 py-2 w-24 flex-shrink-0">Severity</div>
      <div className="hidden sm:block px-3 py-2 w-32 flex-shrink-0">Analyzer</div>
      <div className="px-3 py-2 w-28 flex-shrink-0">Subject</div>
      <div className="px-3 py-2 flex-1 min-w-0">Finding</div>
      <div className="hidden sm:block px-3 py-2 w-20 flex-shrink-0">Confidence</div>
      {onStatusChange && <div className="px-3 py-2 w-28 flex-shrink-0">Status</div>}
      {analysisId !== undefined && <div className="px-3 py-2 w-10 flex-shrink-0"></div>}
    </div>
  );
}

export function FindingsTable({
  findings,
  onSelect,
  onStatusChange,
  selectedIds,
  onToggleSelected,
  onSubjectClick,
  analysisId,
  highlightedIndex,
}: Props) {
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const parentRef = useRef<HTMLDivElement>(null);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    return () => {
      if (copyTimerRef.current !== undefined) {
        clearTimeout(copyTimerRef.current);
      }
    };
  }, []);

  const shouldVirtualize = findings.length > VIRTUALIZE_THRESHOLD;

  const virtualizer = useVirtualizer({
    count: findings.length,
    getScrollElement: () => (shouldVirtualize ? parentRef.current : null),
    estimateSize: () => ROW_HEIGHT,
    overscan: 5,
    enabled: shouldVirtualize,
  });

  useEffect(() => {
    if (highlightedIndex === undefined) return;
    if (shouldVirtualize) {
      virtualizer.scrollToIndex(highlightedIndex, { align: "auto" });
    }
  }, [highlightedIndex, shouldVirtualize, virtualizer]);

  function handleCopyLink(e: React.MouseEvent, findingId: number) {
    e.stopPropagation();
    const url = `${window.location.origin}/analyses/${analysisId}?finding=${findingId}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopiedId(findingId);
      if (copyTimerRef.current !== undefined) {
        clearTimeout(copyTimerRef.current);
      }
      copyTimerRef.current = setTimeout(() => setCopiedId(null), 1500);
    });
  }

  if (findings.length === 0) {
    return <p className="text-slate-500">No findings match the current filters.</p>;
  }

  const rowProps = {
    onSelect,
    onStatusChange,
    selectedIds,
    onToggleSelected,
    onSubjectClick,
    analysisId,
    copiedId,
    onCopyLink: handleCopyLink,
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <TableHeader
        onToggleSelected={onToggleSelected}
        onStatusChange={onStatusChange}
        analysisId={analysisId}
      />
      {shouldVirtualize ? (
        <div
          ref={parentRef}
          style={{ height: CONTAINER_HEIGHT, overflowY: "auto" }}
        >
          <div
            className="min-w-[640px]"
            style={{
              height: virtualizer.getTotalSize(),
              width: "100%",
              position: "relative",
            }}
          >
            {virtualizer.getVirtualItems().map((virtualItem) => {
              const finding = findings[virtualItem.index];
              return (
                <FindingRow
                  key={finding.id}
                  f={finding}
                  {...rowProps}
                  highlighted={highlightedIndex === virtualItem.index}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: virtualItem.size,
                    transform: `translateY(${virtualItem.start}px)`,
                  }}
                />
              );
            })}
          </div>
        </div>
      ) : (
        <div className="min-w-[640px]">
          {findings.map((f, idx) => (
            <FindingRow key={f.id} f={f} {...rowProps} highlighted={highlightedIndex === idx} />
          ))}
        </div>
      )}
    </div>
  );
}
