import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { FindingsFilterBar } from "../components/FindingsFilterBar";
import { FindingsTable } from "../components/FindingsTable";
import type { Finding } from "../lib/types";

const defaultFilterBarProps = {
  severityFilter: ["critical", "major", "minor"] as const,
  onToggleSeverity: vi.fn(),
  analyzerFilter: "all" as const,
  onChangeAnalyzer: vi.fn(),
  search: "",
  onChangeSearch: vi.fn(),
  filteredCount: 5,
  totalCount: 10,
  onExportCsv: vi.fn(),
  statusFilter: ["open", "in_review"] as const,
  onToggleStatus: vi.fn(),
  minConfidence: 0,
  onChangeMinConfidence: vi.fn(),
};

function makeFindings(count = 3): Finding[] {
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    analyzer: "visit_windows" as const,
    severity: "major" as const,
    subject_id: `subj-${i + 1}`,
    summary: `Finding ${i + 1}`,
    detail: "details",
    protocol_citation: "§1",
    data_citation: {},
    confidence: 0.9,
    status: "open" as const,
    assignee: null,
    notes: null,
    updated_at: null,
  }));
}

describe("ResponsiveLayout – FindingsFilterBar", () => {
  it("has flex-wrap on the inner controls container", () => {
    const { container } = render(<FindingsFilterBar {...defaultFilterBarProps} />);
    // The inner div containing all controls should have flex-wrap
    const flexWrappedDiv = container.querySelector(".flex-wrap");
    expect(flexWrappedDiv).not.toBeNull();
  });
});

describe("ResponsiveLayout – FindingsTable", () => {
  it("wraps the table in a container with overflow-x-auto", () => {
    const { container } = render(<FindingsTable findings={makeFindings()} />);
    const scrollable = container.querySelector(".overflow-x-auto");
    expect(scrollable).not.toBeNull();
  });

  it("hides the Analyzer column on mobile (element or its direct wrapper has 'hidden' in className)", () => {
    render(<FindingsTable findings={makeFindings()} />);
    // The Analyzer header cell element itself should have a class that hides it on mobile
    const analyzerHeader = screen.getByText("Analyzer");
    const parent = analyzerHeader.parentElement;
    const hasHiddenClass =
      analyzerHeader.className.split(" ").includes("hidden") ||
      (parent !== null && parent.className.split(" ").includes("hidden"));
    expect(hasHiddenClass).toBe(true);
  });

  it("hides the Confidence column on mobile (element or its direct wrapper has 'hidden' in className)", () => {
    render(<FindingsTable findings={makeFindings()} />);
    // The Confidence header cell element itself should have a class that hides it on mobile
    const confidenceHeader = screen.getByText("Confidence");
    const parent = confidenceHeader.parentElement;
    const hasHiddenClass =
      confidenceHeader.className.split(" ").includes("hidden") ||
      (parent !== null && parent.className.split(" ").includes("hidden"));
    expect(hasHiddenClass).toBe(true);
  });
});
