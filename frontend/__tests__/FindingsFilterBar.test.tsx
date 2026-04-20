import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { FindingsFilterBar } from "../components/FindingsFilterBar";

const defaultProps = {
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

describe("FindingsFilterBar – confidence slider (D4)", () => {
  it('shows "All confidence" label when minConfidence is 0', () => {
    render(<FindingsFilterBar {...defaultProps} minConfidence={0} />);
    expect(screen.getByText("All confidence")).toBeInTheDocument();
  });

  it('shows "≥ 50%" label when minConfidence is 0.5', () => {
    render(<FindingsFilterBar {...defaultProps} minConfidence={0.5} />);
    expect(screen.getByText("≥ 50%")).toBeInTheDocument();
  });

  it('shows "≥ 80%" label when minConfidence is 0.8', () => {
    render(<FindingsFilterBar {...defaultProps} minConfidence={0.8} />);
    expect(screen.getByText("≥ 80%")).toBeInTheDocument();
  });

  it("renders a range slider with correct attributes", () => {
    render(<FindingsFilterBar {...defaultProps} minConfidence={0} />);
    const slider = screen.getByRole("slider");
    expect(slider).toHaveAttribute("type", "range");
    expect(slider).toHaveAttribute("min", "0");
    expect(slider).toHaveAttribute("max", "1");
    expect(slider).toHaveAttribute("step", "0.05");
  });

  it("calls onChangeMinConfidence with parsed float on change", () => {
    const onChangeMinConfidence = vi.fn();
    render(
      <FindingsFilterBar
        {...defaultProps}
        minConfidence={0}
        onChangeMinConfidence={onChangeMinConfidence}
      />,
    );
    const slider = screen.getByRole("slider");
    fireEvent.change(slider, { target: { value: "0.5" } });
    expect(onChangeMinConfidence).toHaveBeenCalledWith(0.5);
  });

  it("slider reflects the current minConfidence value", () => {
    render(<FindingsFilterBar {...defaultProps} minConfidence={0.35} />);
    const slider = screen.getByRole("slider") as HTMLInputElement;
    expect(slider.value).toBe("0.35");
  });
});
