"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ProtocolUploader } from "@/components/ProtocolUploader";
import { DatasetUploader } from "@/components/DatasetUploader";
import { RunAnalysisButton } from "@/components/RunAnalysisButton";
import type { Protocol, Dataset } from "@/lib/types";

export default function Home() {
  const [protocol, setProtocol] = useState<Protocol | null>(null);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const router = useRouter();

  return (
    <main className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold">Clinical Monitoring Copilot</h1>
        <p className="text-slate-600">
          Upload a protocol and patient dataset to detect deviations.
        </p>
      </header>
      <ProtocolUploader onUploaded={setProtocol} />
      {protocol && (
        <p className="text-sm text-slate-700">
          Protocol loaded: <b>{protocol.study_id}</b>
        </p>
      )}
      <DatasetUploader onUploaded={setDataset} />
      {dataset && (
        <p className="text-sm text-slate-700">
          Dataset loaded: <b>{dataset.name}</b>
        </p>
      )}
      <RunAnalysisButton
        protocolId={protocol?.id ?? null}
        datasetId={dataset?.id ?? null}
        onStarted={(a) => router.push(`/analyses/${a.id}`)}
      />
    </main>
  );
}
