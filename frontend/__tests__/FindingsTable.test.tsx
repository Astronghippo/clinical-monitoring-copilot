import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
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

describe("FindingsTable – virtualization", () => {
  it("does not render all 100 rows when given 100 findings (virtualization active)", () => {
    // Save original descriptor so we can restore it faithfully after the test
    const originalDescriptor = Object.getOwnPropertyDescriptor(
      HTMLElement.prototype,
      "offsetHeight",
    );

    // Mock offsetHeight so the virtualizer sees a 600px container in jsdom
    Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
      configurable: true,
      get() {
        return 600;
      },
    });

    const manyFindings = Array.from({ length: 100 }, (_, i) =>
      f({ id: i + 1, subject_id: `subj-${i + 1}` }),
    );
    render(<FindingsTable findings={manyFindings} />);
    // With virtualization, only a window of rows is rendered — far fewer than 100
    const rows = document.querySelectorAll("[data-testid^='finding-row-']");
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.length).toBeLessThan(100);

    // Restore original descriptor (or remove the override if there was none)
    if (originalDescriptor) {
      Object.defineProperty(HTMLElement.prototype, "offsetHeight", originalDescriptor);
    } else {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (HTMLElement.prototype as any).offsetHeight;
    }
  });

  it("renders all rows when given 5 findings (small lists show everything)", () => {
    const fewFindings = Array.from({ length: 5 }, (_, i) =>
      f({ id: i + 1, subject_id: `subj-${i + 1}` }),
    );
    render(<FindingsTable findings={fewFindings} />);
    const rows = document.querySelectorAll("[data-testid^='finding-row-']");
    expect(rows.length).toBe(5);
  });
});

describe("FindingsTable – copy link button", () => {
  let writeText: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      writable: true,
      configurable: true,
    });
    // Provide a stable origin so we can assert the URL
    Object.defineProperty(window, "location", {
      value: { ...window.location, origin: "https://example.com" },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders a copy-link button for each row when analysisId is provided", () => {
    render(
      <FindingsTable
        findings={[f({ id: 7 }), f({ id: 8 })]}
        analysisId={5}
      />,
    );
    const buttons = screen.getAllByRole("button", { name: /copy link to finding/i });
    expect(buttons).toHaveLength(2);
  });

  it("does not render copy-link buttons when analysisId is omitted", () => {
    render(<FindingsTable findings={[f({ id: 7 })]} />);
    expect(
      screen.queryByRole("button", { name: /copy link to finding/i }),
    ).toBeNull();
  });

  it("copies the correct URL to clipboard on click", async () => {
    render(
      <FindingsTable
        findings={[f({ id: 42 })]}
        analysisId={5}
      />,
    );
    const btn = screen.getByRole("button", { name: /copy link to finding/i });
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(writeText).toHaveBeenCalledWith(
      "https://example.com/analyses/5?finding=42",
    );
  });

  it("shows a ✓ confirmation after copying that disappears after 1.5 s", async () => {
    vi.useFakeTimers();
    render(
      <FindingsTable
        findings={[f({ id: 42 })]}
        analysisId={5}
      />,
    );
    const btn = screen.getByRole("button", { name: /copy link to finding/i });
    await act(async () => {
      fireEvent.click(btn);
    });
    // Confirmation tick should be visible immediately after click
    expect(screen.getByText("✓")).toBeInTheDocument();
    // After 1.5 s it should disappear
    act(() => {
      vi.advanceTimersByTime(1500);
    });
    expect(screen.queryByText("✓")).toBeNull();
  });
});
