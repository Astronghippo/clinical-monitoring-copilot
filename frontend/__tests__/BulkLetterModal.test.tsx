import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BulkLetterModal } from "../components/BulkLetterModal";

const mockLetter = (id: number) => ({
  subject_line: `Query for finding ${id}`,
  body: `Body of letter ${id}`,
  reply_by: "2026-05-01",
});

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("BulkLetterModal", () => {
  it("calls api.draftQueryLetter for each findingId", async () => {
    const draftQueryLetter = vi
      .fn()
      .mockImplementation((id: number) => Promise.resolve(mockLetter(id)));

    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      draftQueryLetter,
    } as never);

    render(<BulkLetterModal findingIds={[1, 2, 3]} onClose={() => {}} />);

    await waitFor(() => expect(draftQueryLetter).toHaveBeenCalledTimes(3));
    expect(draftQueryLetter).toHaveBeenCalledWith(1);
    expect(draftQueryLetter).toHaveBeenCalledWith(2);
    expect(draftQueryLetter).toHaveBeenCalledWith(3);
  });

  it("shows progress text during generation", async () => {
    // draftQueryLetter never resolves so we can observe the in-progress state
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      draftQueryLetter: () => new Promise(() => {}),
    } as never);

    render(<BulkLetterModal findingIds={[1, 2]} onClose={() => {}} />);

    // Should show some progress indicator with total count
    await waitFor(() =>
      expect(screen.getByText(/drafting.*2/i)).toBeInTheDocument(),
    );
  });

  it("shows Download .txt button after all letters complete", async () => {
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      draftQueryLetter: (id: number) => Promise.resolve(mockLetter(id)),
    } as never);

    render(<BulkLetterModal findingIds={[1, 2]} onClose={() => {}} />);

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /download.*\.txt/i }),
      ).toBeInTheDocument(),
    );
  });

  it("shows error count when some letters fail", async () => {
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      draftQueryLetter: (id: number) =>
        id === 2
          ? Promise.reject(new Error("API error"))
          : Promise.resolve(mockLetter(id)),
    } as never);

    render(<BulkLetterModal findingIds={[1, 2, 3]} onClose={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText(/1.*failed/i)).toBeInTheDocument(),
    );
  });

  it("still shows Download button for successful letters when some fail", async () => {
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      draftQueryLetter: (id: number) =>
        id === 2
          ? Promise.reject(new Error("API error"))
          : Promise.resolve(mockLetter(id)),
    } as never);

    render(<BulkLetterModal findingIds={[1, 2]} onClose={() => {}} />);

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /download.*\.txt/i }),
      ).toBeInTheDocument(),
    );
  });

  it("calls onClose when Close button is clicked", async () => {
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      draftQueryLetter: (id: number) => Promise.resolve(mockLetter(id)),
    } as never);

    const onClose = vi.fn();
    render(<BulkLetterModal findingIds={[1]} onClose={onClose} />);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^close$/i })).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole("button", { name: /^close$/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it("has role=dialog with aria-label for accessibility", async () => {
    vi.spyOn(await import("../lib/api"), "api", "get").mockReturnValue({
      draftQueryLetter: () => new Promise(() => {}),
    } as never);

    render(<BulkLetterModal findingIds={[1]} onClose={() => {}} />);

    expect(
      screen.getByRole("dialog", { name: /bulk query letter drafting/i }),
    ).toBeInTheDocument();
  });
});
