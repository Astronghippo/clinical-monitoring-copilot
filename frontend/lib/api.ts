import type {
  Analysis,
  AnalysisSummary,
  Dataset,
  Protocol,
  QueryLetter,
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
  draftQueryLetter: async (findingId: number): Promise<QueryLetter> =>
    json(
      await fetch(`${BASE}/findings/${findingId}/query-letter`, {
        method: "POST",
      }),
    ),
};
