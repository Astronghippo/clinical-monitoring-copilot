import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../lib/api";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("api", () => {
  it("uploadProtocol posts FormData", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 1, study_id: "X", filename: "x.pdf", created_at: "2026-01-01",
        }),
        { status: 200 },
      ),
    );
    const f = new File(["%PDF-"], "x.pdf", { type: "application/pdf" });
    const p = await api.uploadProtocol(f);
    expect(p.id).toBe(1);
    expect(fetchMock.mock.calls[0][1]?.method).toBe("POST");
  });

  it("runAnalysis sends JSON body", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 5, protocol_id: 1, dataset_id: 2, status: "pending",
          created_at: "2026-01-01", findings: [],
        }),
        { status: 200 },
      ),
    );
    const a = await api.runAnalysis(1, 2);
    expect(a.id).toBe(5);
    const call = fetchMock.mock.calls[0];
    expect(call[1]?.headers).toMatchObject({ "Content-Type": "application/json" });
  });

  it("getAnalysis GETs the endpoint", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 7, protocol_id: 1, dataset_id: 2, status: "done",
          created_at: "2026-01-01", findings: [],
        }),
        { status: 200 },
      ),
    );
    const a = await api.getAnalysis(7);
    expect(a.status).toBe("done");
  });
});
