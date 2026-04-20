export type Severity = "critical" | "major" | "minor";
export type AnalyzerKind = "visit_windows" | "completeness" | "eligibility" | "plausibility";
export type FindingStatus = "open" | "in_review" | "resolved" | "false_positive";

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
  status: FindingStatus;
  assignee: string | null;
  notes: string | null;
  updated_at: string | null;
}

export interface Analysis {
  id: number;
  protocol_id: number;
  dataset_id: number;
  status: "pending" | "running" | "done" | "error";
  name: string | null;
  created_at: string;
  findings: Finding[];
}

export interface AnalysisSummary {
  id: number;
  protocol_id: number;
  dataset_id: number;
  status: "pending" | "running" | "done" | "error";
  name: string | null;
  created_at: string;
  study_id: string | null;
  finding_count: number;
  counts: { critical: number; major: number; minor: number };
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

export interface FindingGroup {
  template: string;
  analyzer: AnalyzerKind;
  severity: Severity;
  count: number;
  subject_ids: string[];
  finding_ids: number[];
}

export interface SiteRollup {
  site_id: string;
  subject_count: number;
  finding_count: number;
  deviation_rate: number;
  counts: { critical: number; major: number; minor: number };
}

export interface SubjectVisit {
  visit_name: string;
  visit_num: number;
  date: string | null;
  has_finding: boolean;
}

export interface SubjectDrilldown {
  findings: Finding[];
  visits: SubjectVisit[];
}

export interface AuditEvent {
  id: number;
  event_type: string;
  subject_kind: "analysis" | "finding" | "protocol";
  subject_id: number;
  actor: string;
  before: unknown;
  after: unknown;
  created_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatReply {
  reply: string;
}

export interface AmendmentDiff {
  added_visits: string[];
  removed_visits: string[];
  changed_visits: string[];
  added_criteria: string[];
  removed_criteria: string[];
  obsolete_finding_ids: number[];
}
