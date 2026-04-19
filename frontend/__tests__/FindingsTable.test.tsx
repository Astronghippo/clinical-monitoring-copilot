import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { FindingsTable } from "../components/FindingsTable";
import type { Finding } from "../lib/types";

function f(overrides: Partial<Finding> = {}): Finding {
  return {
    id: 1,
    analyzer: "visit_windows",
    severity: "major",
    subject_id: "1001",
    summary: "Visit V3 late by 5 days",
    detail: "details",
    protocol_citation: "§6",
    data_citation: {},
    confidence: 1.0,
    status: "open",
    assignee: null,
    notes: null,
    updated_at: null,
    ...overrides,
  };
}

describe("FindingsTable", () => {
  it("renders empty state", () => {
    render(<FindingsTable findings={[]} />);
    expect(screen.getByText(/no findings/i)).toBeInTheDocument();
  });

  it("renders one row per finding", () => {
    render(
      <FindingsTable
        findings={[f(), f({ id: 2, severity: "critical", subject_id: "1012" })]}
      />,
    );
    expect(screen.getByText("1001")).toBeInTheDocument();
    expect(screen.getByText("1012")).toBeInTheDocument();
    expect(screen.getByText("critical")).toBeInTheDocument();
  });

  it("invokes onSelect when row clicked", () => {
    const onSelect = vi.fn();
    render(<FindingsTable findings={[f()]} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("finding-row-1"));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }));
  });

  it("shows confidence as percent", () => {
    render(<FindingsTable findings={[f({ confidence: 0.85 })]} />);
    expect(screen.getByText("85%")).toBeInTheDocument();
  });
});
