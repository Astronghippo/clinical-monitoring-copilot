import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FindingDetail } from "../components/FindingDetail";
import type { Finding } from "../lib/types";

const f: Finding = {
  id: 1,
  analyzer: "eligibility",
  severity: "critical",
  subject_id: "1012",
  summary: "E2 violation",
  detail: "HbA1c 11.2% exceeds cutoff 10.5%",
  protocol_citation: "Eligibility, E2",
  data_citation: { domain: "DM", usubjid: "1012" },
  confidence: 0.8,
};

describe("FindingDetail", () => {
  it("renders summary, detail, and citations", () => {
    render(<FindingDetail finding={f} onClose={() => {}} />);
    expect(screen.getByText("E2 violation")).toBeInTheDocument();
    expect(screen.getByText(/exceeds cutoff/i)).toBeInTheDocument();
    expect(screen.getByText(/Eligibility, E2/)).toBeInTheDocument();
  });

  it("shows confidence as percent in subject line", () => {
    render(<FindingDetail finding={f} onClose={() => {}} />);
    expect(screen.getByText(/80%/)).toBeInTheDocument();
  });

  it("renders data_citation as formatted JSON", () => {
    render(<FindingDetail finding={f} onClose={() => {}} />);
    // pre block contains the JSON — fragment match
    expect(screen.getByText(/"usubjid": "1012"/)).toBeInTheDocument();
  });

  it("invokes onClose when close button clicked", () => {
    const onClose = vi.fn();
    render(<FindingDetail finding={f} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalled();
  });
});
