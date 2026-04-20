import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { NLFilterBar } from "../components/NLFilterBar";

vi.mock("../lib/api", () => ({
  api: {
    nlFilter: vi.fn(),
  },
}));

import { api } from "../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("NLFilterBar", () => {
  it("renders a search input with placeholder text", () => {
    render(<NLFilterBar analysisId={1} onFiltersApplied={() => {}} />);
    expect(screen.getByPlaceholderText(/search in plain english/i)).toBeInTheDocument();
  });

  it("renders an 'Ask Claude' button", () => {
    render(<NLFilterBar analysisId={1} onFiltersApplied={() => {}} />);
    expect(screen.getByRole("button", { name: /ask claude/i })).toBeInTheDocument();
  });

  it("calls api.nlFilter with analysisId and query on submit", async () => {
    vi.mocked(api.nlFilter).mockResolvedValue({
      analyzer: "eligibility",
      severity: ["critical"],
      status: null,
      search_text: null,
    });
    const onFilters = vi.fn();

    render(<NLFilterBar analysisId={5} onFiltersApplied={onFilters} />);
    fireEvent.change(screen.getByPlaceholderText(/search in plain english/i), {
      target: { value: "show critical eligibility findings" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask claude/i }));

    await waitFor(() => {
      expect(api.nlFilter).toHaveBeenCalledWith(5, "show critical eligibility findings");
    });
  });

  it("calls onFiltersApplied with translated filter params", async () => {
    const filters = {
      analyzer: "plausibility",
      severity: ["major"],
      status: ["open"],
      search_text: "HbA1c",
    };
    vi.mocked(api.nlFilter).mockResolvedValue(filters);
    const onFilters = vi.fn();

    render(<NLFilterBar analysisId={1} onFiltersApplied={onFilters} />);
    fireEvent.change(screen.getByPlaceholderText(/search in plain english/i), {
      target: { value: "open plausibility major findings with HbA1c" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask claude/i }));

    await waitFor(() => {
      expect(onFilters).toHaveBeenCalledWith(filters);
    });
  });

  it("shows an error on API failure", async () => {
    vi.mocked(api.nlFilter).mockRejectedValue(new Error("Service unavailable"));

    render(<NLFilterBar analysisId={1} onFiltersApplied={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/search in plain english/i), {
      target: { value: "broken query" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask claude/i }));

    await waitFor(() => {
      expect(screen.getByText(/service unavailable/i)).toBeInTheDocument();
    });
  });

  it("disables button while loading", async () => {
    let resolve!: (v: object) => void;
    vi.mocked(api.nlFilter).mockReturnValue(new Promise((r) => { resolve = r; }));

    render(<NLFilterBar analysisId={1} onFiltersApplied={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/search in plain english/i), {
      target: { value: "query" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask claude/i }));

    expect(screen.getByRole("button", { name: /asking/i })).toBeDisabled();
    resolve({ analyzer: null, severity: null, status: null, search_text: null });
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /asking/i })).not.toBeInTheDocument();
    });
  });

  it("shows a clear button after filters are applied", async () => {
    vi.mocked(api.nlFilter).mockResolvedValue({
      analyzer: "eligibility",
      severity: null,
      status: null,
      search_text: null,
    });

    render(<NLFilterBar analysisId={1} onFiltersApplied={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/search in plain english/i), {
      target: { value: "eligibility findings" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask claude/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /clear/i })).toBeInTheDocument();
    });
  });
});
