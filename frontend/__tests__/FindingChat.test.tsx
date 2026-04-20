import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FindingChat } from "../components/FindingChat";
import type { Finding } from "../lib/types";

const f: Finding = {
  id: 7,
  analyzer: "eligibility",
  severity: "critical",
  subject_id: "1012",
  summary: "E2 violation: HbA1c too high",
  detail: "HbA1c 11.2% exceeds maximum 10.5%",
  protocol_citation: "Section 5.2",
  data_citation: { domain: "LB" },
  confidence: 0.95,
  status: "open",
  assignee: null,
  notes: null,
  updated_at: null,
};

// Mock the api module
vi.mock("../lib/api", () => ({
  api: {
    chatFinding: vi.fn(),
  },
}));

import { api } from "../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("FindingChat", () => {
  it("renders the chat input and a send button", () => {
    render(<FindingChat finding={f} />);
    expect(screen.getByPlaceholderText(/ask/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
  });

  it("shows a starter prompt chip for 'Why was this flagged?'", () => {
    render(<FindingChat finding={f} />);
    expect(screen.getByText(/why was this flagged/i)).toBeInTheDocument();
  });

  it("sends the message when form is submitted and shows reply", async () => {
    vi.mocked(api.chatFinding).mockResolvedValue({
      reply: "HbA1c exceeded the cutoff in Section 5.2.",
    });

    render(<FindingChat finding={f} />);

    fireEvent.change(screen.getByPlaceholderText(/ask/i), {
      target: { value: "Why was this flagged?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/HbA1c exceeded the cutoff/i),
      ).toBeInTheDocument();
    });
  });

  it("calls api.chatFinding with finding id, message, and empty history on first turn", async () => {
    vi.mocked(api.chatFinding).mockResolvedValue({ reply: "Because…" });

    render(<FindingChat finding={f} />);
    fireEvent.change(screen.getByPlaceholderText(/ask/i), {
      target: { value: "Why?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(api.chatFinding).toHaveBeenCalledWith(7, "Why?", []);
    });
  });

  it("accumulates history and passes it on the second turn", async () => {
    vi.mocked(api.chatFinding)
      .mockResolvedValueOnce({ reply: "First answer" })
      .mockResolvedValueOnce({ reply: "Second answer" });

    render(<FindingChat finding={f} />);

    // First turn
    fireEvent.change(screen.getByPlaceholderText(/ask/i), {
      target: { value: "First question" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => screen.getByText("First answer"));

    // Second turn
    fireEvent.change(screen.getByPlaceholderText(/ask/i), {
      target: { value: "Second question" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      const [, , history] = vi.mocked(api.chatFinding).mock.calls[1];
      expect(history).toHaveLength(2);
      expect(history[0]).toEqual({ role: "user", content: "First question" });
      expect(history[1]).toEqual({ role: "assistant", content: "First answer" });
    });
  });

  it("shows a loading indicator while waiting for reply", async () => {
    let resolve!: (v: { reply: string }) => void;
    vi.mocked(api.chatFinding).mockReturnValue(
      new Promise((r) => { resolve = r; }),
    );

    render(<FindingChat finding={f} />);
    fireEvent.change(screen.getByPlaceholderText(/ask/i), {
      target: { value: "Why?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    resolve({ reply: "Done" });
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /send/i })).not.toBeDisabled();
    });
  });

  it("shows an error message if the API call fails", async () => {
    vi.mocked(api.chatFinding).mockRejectedValue(new Error("Network error"));

    render(<FindingChat finding={f} />);
    fireEvent.change(screen.getByPlaceholderText(/ask/i), {
      target: { value: "Why?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  it("clicking a starter chip populates the input", () => {
    render(<FindingChat finding={f} />);
    fireEvent.click(screen.getByText(/why was this flagged/i));
    expect(
      (screen.getByPlaceholderText(/ask/i) as HTMLInputElement).value,
    ).toMatch(/why was this flagged/i);
  });
});
