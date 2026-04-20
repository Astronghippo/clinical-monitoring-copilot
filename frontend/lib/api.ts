import type {
  AmendmentDiff,
  Analysis,
  AnalysisSummary,
  AuditEvent,
  ChatMessage,
  ChatReply,
  Dataset,
  Finding,
  FindingGroup,
  FindingStatus,
  Protocol,
  ProtocolSpec,
  QueryLetter,
  SiteRollup,
  SubjectDrilldown,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

export const api = {
  uploadProtocol: async (file: File): Promise<Protocol> => {
    const fd = new FormData();
    fd.append("file", file);
    return json(await fetch(`${BASE}/protocols`, { method: "POST", body: fd }));
  },
  getProtocol: async (id: number): Promise<Protocol> =>
    json(await fetch(`${BASE}/protocols/${id}`)),
  uploadDataset: async (name: string, files: File[]): Promise<Dataset> => {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    return json(
      await fetch(
        `${BASE}/datasets?name=${encodeURIComponent(name)}`,
        { method: "POST", body: fd },
      ),
    );
  },
  runAnalysis: async (protocol_id: number, dataset_id: number): Promise<Analysis> =>
    json(
      await fetch(`${BASE}/analyses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ protocol_id, dataset_id }),
      }),
    ),
  getAnalysis: async (id: number): Promise<Analysis> =>
    json(await fetch(`${BASE}/analyses/${id}`)),
  listAnalyses: async (): Promise<AnalysisSummary[]> =>
    json(await fetch(`${BASE}/analyses`)),
  renameAnalysis: async (id: number, name: string | null): Promise<Analysis> =>
    json(
      await fetch(`${BASE}/analyses/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      }),
    ),
  cancelAnalysis: async (id: number): Promise<Analysis> =>
    json(
      await fetch(`${BASE}/analyses/${id}/cancel`, { method: "POST" }),
    ),
  generateDigest: async (analysisId: number): Promise<{ digest: string }> =>
    json(
      await fetch(`${BASE}/analyses/${analysisId}/digest`, { method: "POST" }),
    ),
  nlFilter: async (
    analysisId: number,
    query: string,
  ): Promise<{
    analyzer: string | null;
    severity: string[] | null;
    status: string[] | null;
    search_text: string | null;
  }> =>
    json(
      await fetch(`${BASE}/analyses/${analysisId}/nl-filter`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      }),
    ),
  draftQueryLetter: async (findingId: number): Promise<QueryLetter> =>
    json(
      await fetch(`${BASE}/findings/${findingId}/query-letter`, {
        method: "POST",
      }),
    ),
  updateFinding: async (
    id: number,
    patch: { status?: FindingStatus; assignee?: string | null; notes?: string | null },
  ): Promise<Finding> =>
    json(
      await fetch(`${BASE}/findings/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      }),
    ),
  bulkUpdateStatus: async (
    findingIds: number[],
    status: FindingStatus,
  ): Promise<{ updated: number }> =>
    json(
      await fetch(`${BASE}/findings/bulk-status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ finding_ids: findingIds, status }),
      }),
    ),
  listGroupedFindings: async (analysisId: number): Promise<FindingGroup[]> =>
    json(await fetch(`${BASE}/analyses/${analysisId}/grouped`)),
  getSiteRollup: async (analysisId: number): Promise<SiteRollup[]> =>
    json(await fetch(`${BASE}/analyses/${analysisId}/sites`)),
  listAuditEvents: async (): Promise<AuditEvent[]> =>
    json(await fetch(`${BASE}/audit`)),
  getSubjectDrilldown: async (
    analysisId: number,
    subjectId: string,
  ): Promise<SubjectDrilldown> =>
    json(await fetch(`${BASE}/analyses/${analysisId}/subjects/${encodeURIComponent(subjectId)}`)),
  chatFinding: async (
    findingId: number,
    message: string,
    history: ChatMessage[],
  ): Promise<ChatReply> =>
    json(
      await fetch(`${BASE}/findings/${findingId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history }),
      }),
    ),
  patchProtocolSpec: async (protocolId: number, spec: ProtocolSpec): Promise<Protocol> =>
    json(await fetch(`${BASE}/protocols/${protocolId}/spec`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec_json: spec }),
    })),
  checkAmendment: async (analysisId: number, file: File): Promise<AmendmentDiff> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/analyses/${analysisId}/amendment-diff`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      let msg = `${res.status} ${res.statusText}`;
      try {
        const body = await res.json() as { detail?: string };
        msg = body.detail ?? msg;
      } catch { /* use status fallback */ }
      throw new Error(msg);
    }
    return res.json();
  },
};
