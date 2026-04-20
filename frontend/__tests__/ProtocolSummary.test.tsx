import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ProtocolSummary } from "../components/ProtocolSummary";
import type { ProtocolSpec } from "../lib/types";

const mockSpec: ProtocolSpec = {
  study_id: "ACME-DM2-302",
  visits: [
    {
      visit_id: "V1",
      name: "Baseline",
      nominal_day: 0,
      window_minus_days: 0,
      window_plus_days: 0,
      required_procedures: ["Vitals", "Labs"],
    },
    {
      visit_id: "V2",
      name: "Week 2",
      nominal_day: 14,
      window_minus_days: 2,
      window_plus_days: 2,
      required_procedures: ["Vitals"],
    },
  ],
  eligibility: [
    {
      criterion_id: "I1",
      kind: "inclusion",
      text: "Adults 18-75 with type 2 diabetes.",
    },
    {
      criterion_id: "E1",
      kind: "exclusion",
      text: "Pregnancy or plans to become pregnant.",
    },
  ],
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("ProtocolSummary", () => {
  it("renders in view mode by default", () => {
    render(<ProtocolSummary spec={mockSpec} protocolId={1} />);
    // Should show visit names in read-only table
    expect(screen.getByText("Baseline")).toBeInTheDocument();
    expect(screen.getByText("Week 2")).toBeInTheDocument();
    // Eligibility text
    expect(screen.getByText(/Adults 18-75/)).toBeInTheDocument();
    // Should not show save/cancel buttons initially
    expect(screen.queryByRole("button", { name: /save/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /cancel/i })).toBeNull();
  });

  it("shows Edit button in view mode", () => {
    render(<ProtocolSummary spec={mockSpec} protocolId={1} />);
    expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
  });

  it("switches to edit mode when Edit is clicked", () => {
    render(<ProtocolSummary spec={mockSpec} protocolId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    // Should show Save and Cancel buttons
    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
    // Should show editable inputs for visit name
    expect(screen.getByDisplayValue("Baseline")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Week 2")).toBeInTheDocument();
  });

  it("Cancel returns to view mode without saving", async () => {
    const mockPatch = vi.fn();
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      patchProtocolSpec: mockPatch,
    } as never);

    render(<ProtocolSummary spec={mockSpec} protocolId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));

    // Modify a field
    const nameInput = screen.getByDisplayValue("Baseline");
    fireEvent.change(nameInput, { target: { value: "Modified Baseline" } });

    // Cancel
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    // Back to view mode - original value shown
    expect(screen.getByText("Baseline")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Modified Baseline")).toBeNull();
    // patchProtocolSpec not called
    expect(mockPatch).not.toHaveBeenCalled();
  });

  it("Save calls api.patchProtocolSpec with updated spec", async () => {
    const updatedProtocol = {
      id: 1,
      study_id: "ACME-DM2-302",
      filename: "test.pdf",
      created_at: "2024-01-01T00:00:00",
      spec_json: { ...mockSpec, visits: [{ ...mockSpec.visits[0], name: "New Baseline" }, mockSpec.visits[1]] },
      parse_status: "done" as const,
    };
    const mockPatch = vi.fn().mockResolvedValue(updatedProtocol);
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      patchProtocolSpec: mockPatch,
    } as never);

    render(<ProtocolSummary spec={mockSpec} protocolId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));

    // Modify visit name
    const nameInput = screen.getByDisplayValue("Baseline");
    fireEvent.change(nameInput, { target: { value: "New Baseline" } });

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(mockPatch).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          visits: expect.arrayContaining([
            expect.objectContaining({ name: "New Baseline" }),
          ]),
        }),
      ),
    );
  });

  it("returns to view mode after successful save", async () => {
    const updatedSpec: ProtocolSpec = {
      ...mockSpec,
      visits: [{ ...mockSpec.visits[0], name: "New Baseline" }, mockSpec.visits[1]],
    };
    const updatedProtocol = {
      id: 1,
      study_id: "ACME-DM2-302",
      filename: "test.pdf",
      created_at: "2024-01-01T00:00:00",
      spec_json: updatedSpec,
      parse_status: "done" as const,
    };
    const mockPatch = vi.fn().mockResolvedValue(updatedProtocol);
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      patchProtocolSpec: mockPatch,
    } as never);

    render(<ProtocolSummary spec={mockSpec} protocolId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));

    const nameInput = screen.getByDisplayValue("Baseline");
    fireEvent.change(nameInput, { target: { value: "New Baseline" } });

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: /save/i })).toBeNull(),
    );
    // Edit button should be back
    expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
  });

  it("shows error when save fails", async () => {
    const mockPatch = vi.fn().mockRejectedValueOnce(new Error("Server error"));
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      patchProtocolSpec: mockPatch,
    } as never);

    render(<ProtocolSummary spec={mockSpec} protocolId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /edit/i }));
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(screen.getByText("Server error")).toBeInTheDocument(),
    );
    // Should still be in edit mode
    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
  });
});
