import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { SiteHeatmap } from "../components/SiteHeatmap";
import type { SiteRollup } from "../lib/types";

function makeSite(overrides: Partial<SiteRollup> = {}): SiteRollup {
  return {
    site_id: "SITE01",
    subject_count: 10,
    finding_count: 15,
    deviation_rate: 1.5,
    counts: { critical: 3, major: 7, minor: 5 },
    ...overrides,
  };
}

const twoSites: SiteRollup[] = [
  makeSite({ site_id: "SITE01", subject_count: 10, finding_count: 15, deviation_rate: 1.5 }),
  makeSite({ site_id: "SITE02", subject_count: 5, finding_count: 5, deviation_rate: 1.0, counts: { critical: 1, major: 2, minor: 2 } }),
];

describe("SiteHeatmap", () => {
  it("renders a row per site", () => {
    render(<SiteHeatmap sites={twoSites} />);
    expect(screen.getByText("SITE01")).toBeInTheDocument();
    expect(screen.getByText("SITE02")).toBeInTheDocument();
  });

  it("renders subject count for each site", () => {
    render(<SiteHeatmap sites={twoSites} />);
    expect(screen.getByTestId("subject-count-SITE01")).toHaveTextContent("10");
    expect(screen.getByTestId("subject-count-SITE02")).toHaveTextContent("5");
  });

  it("renders total finding count for each site", () => {
    render(<SiteHeatmap sites={twoSites} />);
    expect(screen.getByTestId("finding-count-SITE01")).toHaveTextContent("15");
    expect(screen.getByTestId("finding-count-SITE02")).toHaveTextContent("5");
  });

  it("renders deviation rate as X.X per subject", () => {
    render(<SiteHeatmap sites={twoSites} />);
    expect(screen.getByTestId("deviation-rate-SITE01")).toHaveTextContent("1.5 per subject");
    expect(screen.getByTestId("deviation-rate-SITE02")).toHaveTextContent("1.0 per subject");
  });

  it("renders severity breakdown counts", () => {
    render(<SiteHeatmap sites={[twoSites[0]]} />);
    expect(screen.getByTestId("critical-count-SITE01")).toHaveTextContent("3");
    expect(screen.getByTestId("major-count-SITE01")).toHaveTextContent("7");
    expect(screen.getByTestId("minor-count-SITE01")).toHaveTextContent("5");
  });

  it("renders empty state when no sites", () => {
    render(<SiteHeatmap sites={[]} />);
    expect(screen.getByText(/no site data/i)).toBeInTheDocument();
  });

  it("sorts by site ID ascending by default", () => {
    const sites = [
      makeSite({ site_id: "SITE03" }),
      makeSite({ site_id: "SITE01" }),
      makeSite({ site_id: "SITE02" }),
    ];
    render(<SiteHeatmap sites={sites} />);
    const rows = screen.getAllByTestId(/^site-row-/);
    expect(rows[0]).toHaveAttribute("data-testid", "site-row-SITE01");
    expect(rows[1]).toHaveAttribute("data-testid", "site-row-SITE02");
    expect(rows[2]).toHaveAttribute("data-testid", "site-row-SITE03");
  });

  it("toggles sort direction on column header click", () => {
    render(<SiteHeatmap sites={twoSites} />);
    const siteIdHeader = screen.getByText(/site id/i);
    // Initially ascending (SITE01 before SITE02)
    let rows = screen.getAllByTestId(/^site-row-/);
    expect(rows[0]).toHaveAttribute("data-testid", "site-row-SITE01");
    // Click to sort descending
    fireEvent.click(siteIdHeader);
    rows = screen.getAllByTestId(/^site-row-/);
    expect(rows[0]).toHaveAttribute("data-testid", "site-row-SITE02");
  });

  it("sorts by subject count when that column is clicked", () => {
    const sites = [
      makeSite({ site_id: "SITE01", subject_count: 10 }),
      makeSite({ site_id: "SITE02", subject_count: 3 }),
      makeSite({ site_id: "SITE03", subject_count: 7 }),
    ];
    render(<SiteHeatmap sites={sites} />);
    const subjectHeader = screen.getByText(/subjects/i);
    fireEvent.click(subjectHeader);
    // ascending by subject count
    const rows = screen.getAllByTestId(/^site-row-/);
    expect(rows[0]).toHaveAttribute("data-testid", "site-row-SITE02"); // 3
    expect(rows[1]).toHaveAttribute("data-testid", "site-row-SITE03"); // 7
    expect(rows[2]).toHaveAttribute("data-testid", "site-row-SITE01"); // 10
  });

  it("sorts by total findings when that column is clicked", () => {
    const sites = [
      makeSite({ site_id: "SITE01", finding_count: 20 }),
      makeSite({ site_id: "SITE02", finding_count: 5 }),
    ];
    render(<SiteHeatmap sites={sites} />);
    const findingsHeader = screen.getByText(/total findings/i);
    fireEvent.click(findingsHeader);
    const rows = screen.getAllByTestId(/^site-row-/);
    expect(rows[0]).toHaveAttribute("data-testid", "site-row-SITE02"); // 5
  });

  it("sorts by deviation rate when that column is clicked", () => {
    const sites = [
      makeSite({ site_id: "SITE01", deviation_rate: 2.0 }),
      makeSite({ site_id: "SITE02", deviation_rate: 0.5 }),
    ];
    render(<SiteHeatmap sites={sites} />);
    const rateHeader = screen.getByText(/deviation rate/i);
    fireEvent.click(rateHeader);
    const rows = screen.getAllByTestId(/^site-row-/);
    expect(rows[0]).toHaveAttribute("data-testid", "site-row-SITE02"); // 0.5
  });
});
