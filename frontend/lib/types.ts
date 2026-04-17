export type Severity = "critical" | "major" | "minor";
export type AnalyzerKind = "visit_windows" | "completeness" | "eligibility";

export interface Finding {
  id: number;
  analyzer: AnalyzerKind;
  severity: Severity;
  subject_id: string;
  summary: string;
  detail: string;
  protocol_citation: string;
  data_citation: Record<string, unknown>;
  confidence: number;
}

export interface Analysis {
  id: number;
  protocol_id: number;
  dataset_id: number;
  status: "pending" | "running" | "done" | "error";
  created_at: string;
  findings: Finding[];
}

export interface Protocol {
  id: number;
  study_id: string;
  filename: string;
  created_at: string;
}

export interface Dataset {
  id: number;
  name: string;
  created_at: string;
}
