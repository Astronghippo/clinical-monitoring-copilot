import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AmendmentDiff } from "../components/AmendmentDiff";

const emptyDiff = {
  added_visits: [],
  removed_visits: [],
  changed_visits: [],
  added_criteria: [],
  removed_criteria: [],
  obsolete_finding_ids: [],
};

const diffWithChanges = {
  added_visits: ["Week 8"],
  removed_visits: ["Week 4"],
  changed_visits: ["Baseline"],
  added_criteria: [],
  removed_criteria: ["HbA1c between 7.5% and 10.5%"],
  obsolete_finding_ids: [42, 57],
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("AmendmentDiff", () => {
  it("renders the upload button", () => {
    render(<AmendmentDiff analysisId={1} findings={[]} onClose={() => {}} />);
    expect(
      screen.getByRole("button", { name: /upload/i }),
    ).toBeInTheDocument();
  });

  it("renders a file input", () => {
    render(<AmendmentDiff analysisId={1} findings={[]} onClose={() => {}} />);
    const input = document.querySelector('input[type="file"]');
    expect(input).not.toBeNull();
  });

  it("shows loading state while submitting", async () => {
    // checkAmendment never resolves so we can observe loading state
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      checkAmendment: () => new Promise(() => {}),
    } as never);

    render(<AmendmentDiff analysisId={1} findings={[]} onClose={() => {}} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["%PDF-"], "amendment.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /upload/i }));

    await waitFor(() =>
      expect(screen.getByText(/loading|checking|parsing/i)).toBeInTheDocument(),
    );
  });

  it("displays diff results when submission succeeds", async () => {
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      checkAmendment: () => Promise.resolve(diffWithChanges),
    } as never);

    render(<AmendmentDiff analysisId={1} findings={[]} onClose={() => {}} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["%PDF-"], "amendment.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /upload/i }));

    await waitFor(() =>
      expect(screen.getByText(/Week 8/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Week 4/)).toBeInTheDocument();
    expect(screen.getByText(/Baseline/)).toBeInTheDocument();
    // Obsolete findings count
    expect(screen.getByText(/2.*finding/i)).toBeInTheDocument();
  });

  it('shows "No relevant changes detected" when diff is empty', async () => {
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      checkAmendment: () => Promise.resolve(emptyDiff),
    } as never);

    render(<AmendmentDiff analysisId={1} findings={[]} onClose={() => {}} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["%PDF-"], "amendment.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /upload/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/no relevant changes detected/i),
      ).toBeInTheDocument(),
    );
  });
});
