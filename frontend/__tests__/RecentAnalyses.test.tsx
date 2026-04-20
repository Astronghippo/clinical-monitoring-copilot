import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

vi.mock("../lib/api", () => ({
  api: { listAnalyses: vi.fn() },
}));

import { api } from "../lib/api";
import { RecentAnalyses } from "../components/RecentAnalyses";

import type { AnalysisSummary } from "../lib/types";

function makeAnalysis(overrides: Partial<AnalysisSummary> = {}): AnalysisSummary {
  return {
    id: 1,
    protocol_id: 1,
    dataset_id: 1,
    status: "done",
    name: null,
    created_at: "2026-01-01T00:00:00Z",
    study_id: "STUDY-001",
    finding_count: 0,
    counts: { critical: 0, major: 0, minor: 0 },
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("RecentAnalyses", () => {
  it("shows analysis name when set", async () => {
    vi.mocked(api.listAnalyses).mockResolvedValue([
      makeAnalysis({ id: 1, name: "Alpha Trial Run", created_at: "2026-03-01T00:00:00Z" }),
    ]);

    render(<RecentAnalyses />);

    await waitFor(() => {
      expect(screen.getByText("Alpha Trial Run")).toBeInTheDocument();
    });
  });

  it("falls back to 'Analysis #N' when name is null", async () => {
    vi.mocked(api.listAnalyses).mockResolvedValue([
      makeAnalysis({ id: 7, name: null, created_at: "2026-03-01T00:00:00Z" }),
    ]);

    render(<RecentAnalyses />);

    await waitFor(() => {
      expect(screen.getByText("Analysis #7")).toBeInTheDocument();
    });
  });

  it("links each item to /analyses/<id>", async () => {
    vi.mocked(api.listAnalyses).mockResolvedValue([
      makeAnalysis({ id: 42, name: "My Analysis", created_at: "2026-03-01T00:00:00Z" }),
    ]);

    render(<RecentAnalyses />);

    await waitFor(() => {
      const link = screen.getByRole("link", { name: /My Analysis/i });
      expect(link).toHaveAttribute("href", "/analyses/42");
    });
  });

  it("shows at most 3 analyses even if API returns more", async () => {
    const analyses = Array.from({ length: 5 }, (_, i) =>
      makeAnalysis({
        id: i + 1,
        name: `Analysis ${i + 1}`,
        created_at: `2026-0${i + 1}-01T00:00:00Z`,
      }),
    );
    vi.mocked(api.listAnalyses).mockResolvedValue(analyses);

    render(<RecentAnalyses />);

    await waitFor(() => {
      // 3 analysis name links + 1 "View all" link = 4 total links
      const links = screen.getAllByRole("link");
      // filter to analysis item links (not the "View all" link)
      const analysisLinks = links.filter((l) =>
        (l.getAttribute("href") ?? "").startsWith("/analyses/"),
      );
      expect(analysisLinks).toHaveLength(3);
    });
  });

  it("sorts by created_at descending and shows most recent 3", async () => {
    const analyses = [
      makeAnalysis({ id: 1, name: "Oldest", created_at: "2026-01-01T00:00:00Z" }),
      makeAnalysis({ id: 2, name: "Middle", created_at: "2026-02-01T00:00:00Z" }),
      makeAnalysis({ id: 3, name: "Newest", created_at: "2026-04-01T00:00:00Z" }),
      makeAnalysis({ id: 4, name: "Second", created_at: "2026-03-01T00:00:00Z" }),
    ];
    vi.mocked(api.listAnalyses).mockResolvedValue(analyses);

    render(<RecentAnalyses />);

    await waitFor(() => {
      expect(screen.getByText("Newest")).toBeInTheDocument();
      expect(screen.getByText("Second")).toBeInTheDocument();
      expect(screen.getByText("Middle")).toBeInTheDocument();
      expect(screen.queryByText("Oldest")).not.toBeInTheDocument();
    });
  });

  it("returns null / renders nothing when list is empty", async () => {
    vi.mocked(api.listAnalyses).mockResolvedValue([]);

    const { container } = render(<RecentAnalyses />);

    await waitFor(() => {
      expect(container).toBeEmptyDOMElement();
    });
  });

  it("renders nothing silently on API error", async () => {
    vi.mocked(api.listAnalyses).mockRejectedValue(new Error("Network failure"));

    const { container } = render(<RecentAnalyses />);

    await waitFor(() => {
      expect(container).toBeEmptyDOMElement();
    });
  });

  it("shows a loading state while fetching", async () => {
    let resolve!: (v: AnalysisSummary[]) => void;
    vi.mocked(api.listAnalyses).mockReturnValue(
      new Promise((r) => { resolve = r; }),
    );

    render(<RecentAnalyses />);

    expect(screen.getByText(/loading recent analyses/i)).toBeInTheDocument();

    resolve([]);
    await waitFor(() => {
      expect(screen.queryByText(/loading recent analyses/i)).not.toBeInTheDocument();
    });
  });

  it("shows a 'View all' link pointing to /analyses", async () => {
    vi.mocked(api.listAnalyses).mockResolvedValue([
      makeAnalysis({ id: 1, name: "Alpha", created_at: "2026-03-01T00:00:00Z" }),
    ]);

    render(<RecentAnalyses />);

    await waitFor(() => {
      const viewAll = screen.getByRole("link", { name: /view all/i });
      expect(viewAll).toHaveAttribute("href", "/analyses");
    });
  });

  it("shows study_id for each analysis", async () => {
    vi.mocked(api.listAnalyses).mockResolvedValue([
      makeAnalysis({ id: 1, name: "Test", study_id: "NCT-12345", created_at: "2026-03-01T00:00:00Z" }),
    ]);

    render(<RecentAnalyses />);

    await waitFor(() => {
      expect(screen.getByText("NCT-12345")).toBeInTheDocument();
    });
  });

  it("shows finding count chips (critical/major/minor)", async () => {
    vi.mocked(api.listAnalyses).mockResolvedValue([
      makeAnalysis({
        id: 1,
        name: "Test",
        created_at: "2026-03-01T00:00:00Z",
        counts: { critical: 2, major: 5, minor: 1 },
      }),
    ]);

    render(<RecentAnalyses />);

    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument(); // critical
      expect(screen.getByText("5")).toBeInTheDocument(); // major
      expect(screen.getByText("1")).toBeInTheDocument(); // minor
    });
  });
});
