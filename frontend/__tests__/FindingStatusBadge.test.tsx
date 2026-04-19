import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FindingStatusBadge } from "../components/FindingStatusBadge";
import type { FindingStatus } from "../lib/types";

describe("FindingStatusBadge", () => {
  it("renders the current status label", () => {
    render(<FindingStatusBadge value="in_review" onChange={() => {}} />);
    expect(screen.getByText(/in review/i)).toBeInTheDocument();
  });

  it("calls onChange when a new status is selected", async () => {
    const onChange = vi.fn().mockResolvedValue(undefined);
    render(<FindingStatusBadge value="open" onChange={onChange} />);
    fireEvent.click(screen.getByRole("button"));
    fireEvent.click(screen.getByText(/^resolved$/i));
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith("resolved" as FindingStatus);
    });
  });

  it("applies severity-style badge colors by status", () => {
    const { container } = render(
      <FindingStatusBadge value="resolved" onChange={() => {}} />,
    );
    expect(container.querySelector(".bg-emerald-100")).toBeTruthy();
  });
});
