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

export interface VisitDef {
  visit_id: string;
  name: string;
  nominal_day: number;
  window_minus_days: number;
  window_plus_days: number;
  required_procedures: string[];
}

export interface EligibilityCriterion {
  criterion_id: string;
  kind: "inclusion" | "exclusion";
  text: string;
}

export interface ProtocolSpec {
  study_id: string;
  visits: VisitDef[];
  eligibility: EligibilityCriterion[];
}

export interface ProtocolOverview {
  study_id: string | null;
  title: string | null;
  short_description: string | null;
  phase: string | null;
  indication: string | null;
  sponsor: string | null;
  design: string | null;
  arms: string[];
  primary_endpoint: string | null;
  secondary_endpoints: string[];
  treatment_duration: string | null;
  sample_size: number | null;
  notable_aspects: string | null;
}

export interface Protocol {
  id: number;
  study_id: string;
  filename: string;
  created_at: string;
  spec_json?: ProtocolSpec | null;
  summary_json?: ProtocolOverview | null;
  parse_status: "parsing" | "done" | "error";
  parse_error?: string | null;
}

export interface Dataset {
  id: number;
  name: string;
  created_at: string;
}

export interface QueryLetter {
  subject_line: string;
  body: string;
  reply_by: string;
}
