"""Run all three analyzers against the synthetic dataset and score
precision/recall vs. data/ground_truth.json.

Usage:
  python scripts/benchmark.py               # real run (needs ANTHROPIC_API_KEY)
  python scripts/benchmark.py --dry-run     # stub LLM; only visit-window findings are real
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
BACKEND_DIR = HERE.parent.parent
REPO_ROOT = BACKEND_DIR.parent

# Make `app.*` imports work when run as a script from repo root
sys.path.insert(0, str(BACKEND_DIR))

from app.services.analyzers.completeness import CompletenessAnalyzer  # noqa: E402
from app.services.analyzers.eligibility import EligibilityAnalyzer  # noqa: E402
from app.services.analyzers.visit_windows import VisitWindowAnalyzer  # noqa: E402
from app.services.dataset_loader import load_dataset  # noqa: E402
from app.services.protocol_parser import (  # noqa: E402
    extract_text_from_pdf_bytes,
    parse_protocol_text,
    ProtocolSpec,
    VisitDef,
    EligibilityCriterion,
)


PROTOCOL_PDF = REPO_ROOT / "data" / "sample_protocol.pdf"
DATA_DIR = REPO_ROOT / "data" / "synthetic"
GT_PATH = REPO_ROOT / "data" / "ground_truth.json"


class _StubLLM:
    """Returns canned responses so the benchmark script can run without an API key."""

    def json_completion(self, *, system, user, max_tokens=4096):
        # Only used by protocol_parser and completeness/eligibility analyzers.
        # For protocol parsing in --dry-run mode, we bypass this and load
        # a hardcoded spec below.
        if "protocol" in system.lower() and "extract" in system.lower():
            return _hardcoded_spec_dict()
        if "missing" in system.lower() or "completeness" in system.lower():
            return {"missing": [], "reasoning": "stub"}
        if "eligibility" in system.lower() or "auditor" in system.lower():
            return {"violations": []}
        return {}


def _hardcoded_spec_dict() -> dict:
    """Spec matching data/sample_protocol.pdf text."""
    return {
        "study_id": "ACME-DM2-302",
        "visits": [
            {"visit_id": "V1", "name": "Baseline", "nominal_day": 0,
             "window_minus_days": 0, "window_plus_days": 0,
             "required_procedures": ["Vitals", "Labs", "ECG"]},
            {"visit_id": "V2", "name": "Week 2", "nominal_day": 14,
             "window_minus_days": 2, "window_plus_days": 2,
             "required_procedures": ["Vitals", "Labs"]},
            {"visit_id": "V3", "name": "Week 4", "nominal_day": 28,
             "window_minus_days": 3, "window_plus_days": 3,
             "required_procedures": ["Vitals", "Labs", "ECG"]},
            {"visit_id": "V4", "name": "Week 8", "nominal_day": 56,
             "window_minus_days": 5, "window_plus_days": 5,
             "required_procedures": ["Vitals", "Labs"]},
            {"visit_id": "V5", "name": "Week 12", "nominal_day": 84,
             "window_minus_days": 7, "window_plus_days": 7,
             "required_procedures": ["Vitals", "Labs", "ECG"]},
        ],
        "eligibility": [
            {"criterion_id": "I1", "kind": "inclusion",
             "text": "Adults 18-75 with type 2 diabetes.", "structured_check": None},
            {"criterion_id": "I2", "kind": "inclusion",
             "text": "HbA1c between 7.0% and 10.5% at screening.", "structured_check": None},
            {"criterion_id": "E1", "kind": "exclusion",
             "text": "Pregnancy or plans to become pregnant.", "structured_check": None},
            {"criterion_id": "E2", "kind": "exclusion",
             "text": "HbA1c > 10.5% at screening.", "structured_check": None},
        ],
        "source_pages": {"visits": [1], "eligibility": [1]},
    }


def _finding_to_key(f) -> str:
    if f.analyzer == "visit_windows":
        parts = f.summary.split()
        visit = parts[2] if len(parts) > 2 else "?"
        return f"{f.subject_id}|visit_window|{visit}"
    if f.analyzer == "completeness":
        parts = f.summary.split()
        visit = parts[2] if len(parts) > 2 else "?"
        proc = f.summary.split(":")[-1].strip() if ":" in f.summary else "?"
        return f"{f.subject_id}|missing_proc|{visit}/{proc}"
    if f.analyzer == "eligibility":
        return f"{f.subject_id}|eligibility|{f.protocol_citation.split(', ')[-1]}"
    return f"{f.subject_id}|{f.analyzer}|?"


def _gt_to_key(g: dict) -> str:
    k = g["kind"]
    sid = g["subject_id"]
    if k == "visit_window":
        return f"{sid}|visit_window|{g['visit']}"
    if k == "missing_proc":
        return f"{sid}|missing_proc|{g['visit']}/{g['procedure']}"
    if k == "eligibility":
        return f"{sid}|eligibility|{g['criterion']}"
    return f"{sid}|{k}|?"


def run_benchmark(dry_run: bool = False) -> tuple[int, int, int]:
    if not DATA_DIR.exists():
        print(f"Synthetic data not found at {DATA_DIR}", file=sys.stderr)
        print("Run: python data/generate_synthetic.py", file=sys.stderr)
        sys.exit(2)

    if dry_run:
        spec = ProtocolSpec.model_validate(_hardcoded_spec_dict())
        llm = _StubLLM()
    else:
        if not PROTOCOL_PDF.exists():
            print(f"Protocol PDF not found at {PROTOCOL_PDF}", file=sys.stderr)
            sys.exit(2)
        print(f"Parsing protocol: {PROTOCOL_PDF}")
        spec = parse_protocol_text(extract_text_from_pdf_bytes(PROTOCOL_PDF.read_bytes()))
        llm = None  # real client

    print(f"Loading dataset: {DATA_DIR}")
    ds = load_dataset(DATA_DIR)

    findings = []
    for name, analyzer in [
        ("visit_windows", VisitWindowAnalyzer()),
        ("completeness", CompletenessAnalyzer(llm=llm) if llm else CompletenessAnalyzer()),
        ("eligibility", EligibilityAnalyzer(llm=llm) if llm else EligibilityAnalyzer()),
    ]:
        print(f"Running {name}…")
        out = analyzer.run(spec=spec, dataset=ds)
        print(f"  {len(out)} findings")
        findings.extend(out)

    ground_truth = json.loads(GT_PATH.read_text())
    gt_keys = {_gt_to_key(g) for g in ground_truth}
    found_keys = {_finding_to_key(f) for f in findings}

    tp = len(gt_keys & found_keys)
    fn = len(gt_keys - found_keys)
    fp = len(found_keys - gt_keys)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    print("\n=== BENCHMARK ===")
    print(f"Ground truth deviations: {len(gt_keys)}")
    print(f"Findings produced:       {len(found_keys)}")
    print(f"True positives:  {tp}")
    print(f"False negatives: {fn}  (missed: {sorted(gt_keys - found_keys)})")
    print(f"False positives: {fp}  (extra:  {sorted(found_keys - gt_keys)})")
    print(f"Precision: {precision:.2%}")
    print(f"Recall:    {recall:.2%}")
    return tp, fn, fp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Use stub LLM (no API key needed). Only visit-window findings are real.")
    args = parser.parse_args()
    run_benchmark(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
