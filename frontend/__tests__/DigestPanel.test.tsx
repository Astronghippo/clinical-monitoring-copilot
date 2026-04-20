import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DigestPanel } from "../components/DigestPanel";

vi.mock("../lib/api", () => ({
  api: {
    generateDigest: vi.fn(),
  },
}));

import { api } from "../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("DigestPanel", () => {
  it("renders a button to generate the digest", () => {
    render(<DigestPanel analysisId={1} />);
    expect(screen.getByRole("button", { name: /generate digest/i })).toBeInTheDocument();
  });

  it("shows digest text after successful generation", async () => {
    vi.mocked(api.generateDigest).mockResolvedValue({
      digest: "Week 12 monitoring summary. Two critical findings remain open.",
    });

    render(<DigestPanel analysisId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /generate digest/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Week 12 monitoring summary/i),
      ).toBeInTheDocument();
    });
  });

  it("calls api.generateDigest with the analysis id", async () => {
    vi.mocked(api.generateDigest).mockResolvedValue({ digest: "ok" });

    render(<DigestPanel analysisId={42} />);
    fireEvent.click(screen.getByRole("button", { name: /generate digest/i }));

    await waitFor(() => {
      expect(api.generateDigest).toHaveBeenCalledWith(42);
    });
  });

  it("shows an error if the API call fails", async () => {
    vi.mocked(api.generateDigest).mockRejectedValue(new Error("Server error"));

    render(<DigestPanel analysisId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /generate digest/i }));

    await waitFor(() => {
      expect(screen.getByText(/server error/i)).toBeInTheDocument();
    });
  });

  it("shows a loading state while generating", async () => {
    let resolve!: (v: { digest: string }) => void;
    vi.mocked(api.generateDigest).mockReturnValue(
      new Promise((r) => { resolve = r; }),
    );

    render(<DigestPanel analysisId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /generate digest/i }));

    expect(screen.getByRole("button", { name: /generating/i })).toBeDisabled();
    resolve({ digest: "done" });
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /generating/i })).not.toBeInTheDocument();
    });
  });

  it("shows a copy button after digest is generated", async () => {
    vi.mocked(api.generateDigest).mockResolvedValue({ digest: "The digest text." });

    render(<DigestPanel analysisId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /generate digest/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    });
  });

  it("shows a regenerate button after digest is generated", async () => {
    vi.mocked(api.generateDigest).mockResolvedValue({ digest: "some text" });

    render(<DigestPanel analysisId={1} />);
    fireEvent.click(screen.getByRole("button", { name: /generate digest/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /regenerate/i })).toBeInTheDocument();
    });
  });
});
