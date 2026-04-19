import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { SubjectPanel } from "../components/SubjectPanel";
import type { SubjectDrilldown } from "../lib/types";

function makeData(overrides: Partial<SubjectDrilldown> = {}): SubjectDrilldown {
  return {
    findings: [
      {
        id: 1,
        analyzer: "visit_windows",
        severity: "critical",
        subject_id: "1001",
        summary: "Baseline labs missing",
        detail: "details",
        protocol_citation: "§6",
        data_citation: { visit: "Baseline" },
        confidence: 0.95,
        status: "open",
        assignee: null,
        notes: null,
        updated_at: null,
      },
      {
        id: 2,
        analyzer: "completeness",
        severity: "major",
        subject_id: "1001",
        summary: "Week 4 window deviation",
        detail: "details",
        protocol_citation: "§7",
        data_citation: { visit: "Week 4" },
        confidence: 0.8,
        status: "in_review",
        assignee: null,
        notes: null,
        updated_at: null,
      },
    ],
    visits: [
      { visit_name: "Baseline", visit_num: 1, date: "2025-01-01", has_finding: true },
      { visit_name: "Week 4", visit_num: 2, date: "2025-01-29", has_finding: true },
      { visit_name: "Week 8", visit_num: 3, date: "2025-02-26", has_finding: false },
    ],
    ...overrides,
  };
}

describe("SubjectPanel", () => {
  it("renders subject header with subject ID", () => {
    render(
      <SubjectPanel subjectId="1001" data={makeData()} onClose={() => {}} />,
    );
    expect(screen.getByText(/Subject 1001/i)).toBeInTheDocument();
  });

  it("renders a close button that calls onClose", () => {
    const onClose = vi.fn();
    render(
      <SubjectPanel subjectId="1001" data={makeData()} onClose={onClose} />,
    );
    const closeBtn = screen.getByRole("button", { name: /close/i });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders visit timeline chips for each visit", () => {
    render(
      <SubjectPanel subjectId="1001" data={makeData()} onClose={() => {}} />,
    );
    expect(screen.getByText("Baseline")).toBeInTheDocument();
    expect(screen.getByText("Week 4")).toBeInTheDocument();
    expect(screen.getByText("Week 8")).toBeInTheDocument();
  });

  it("visit chips with findings are red", () => {
    render(
      <SubjectPanel subjectId="1001" data={makeData()} onClose={() => {}} />,
    );
    const baseline = screen.getByTestId("visit-chip-Baseline");
    expect(baseline.className).toMatch(/red/);
  });

  it("visit chips without findings are green", () => {
    render(
      <SubjectPanel subjectId="1001" data={makeData()} onClose={() => {}} />,
    );
    const week8 = screen.getByTestId("visit-chip-Week 8");
    expect(week8.className).toMatch(/green/);
  });

  it("renders finding cards with severity and summary", () => {
    render(
      <SubjectPanel subjectId="1001" data={makeData()} onClose={() => {}} />,
    );
    expect(screen.getByText("Baseline labs missing")).toBeInTheDocument();
    expect(screen.getByText("Week 4 window deviation")).toBeInTheDocument();
    expect(screen.getByText("critical")).toBeInTheDocument();
    expect(screen.getByText("major")).toBeInTheDocument();
  });

  it("renders analyzer name on finding cards", () => {
    render(
      <SubjectPanel subjectId="1001" data={makeData()} onClose={() => {}} />,
    );
    // Analyzer labels should appear on the finding cards
    expect(screen.getByText(/visit window/i)).toBeInTheDocument();
    expect(screen.getByText(/completeness/i)).toBeInTheDocument();
  });

  it("renders status badge on finding cards", () => {
    render(
      <SubjectPanel subjectId="1001" data={makeData()} onClose={() => {}} />,
    );
    expect(screen.getByText(/open/i)).toBeInTheDocument();
    expect(screen.getByText(/in.review/i)).toBeInTheDocument();
  });

  it("renders loading state when data is null", () => {
    render(
      <SubjectPanel subjectId="1001" data={null} onClose={() => {}} />,
    );
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});
