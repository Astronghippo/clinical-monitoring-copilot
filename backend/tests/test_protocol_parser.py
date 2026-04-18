import json
from pathlib import Path

from app.services.protocol_parser import (
    ProtocolSpec,
    extract_relevant_excerpt,
    extract_text_from_pdf_bytes,
    parse_protocol_text,
)

FIX = Path(__file__).parent / "fixtures"


class StubLLM:
    def __init__(self, payload: dict):
        self._p = payload
        self.last_user: str | None = None

    def json_completion(self, *, system, user, max_tokens=4096):
        self.last_user = user
        return self._p


def test_parse_protocol_text_returns_spec():
    expected = json.loads((FIX / "mini_protocol_spec.json").read_text())
    llm = StubLLM(expected)
    text = (FIX / "mini_protocol.txt").read_text()
    spec = parse_protocol_text(text, llm=llm)
    assert isinstance(spec, ProtocolSpec)
    assert spec.study_id == "ACME-DM2-302"
    assert len(spec.visits) == 3
    assert spec.visits[1].window_plus_days == 2
    assert any(c.criterion_id == "E2" for c in spec.eligibility)


def test_extract_text_from_pdf_bytes_roundtrip(tmp_path):
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    pdf_path = tmp_path / "blank.pdf"
    with open(pdf_path, "wb") as f:
        w.write(f)
    text = extract_text_from_pdf_bytes(pdf_path.read_bytes())
    assert isinstance(text, str)


# ---------- Excerpt extraction ----------

def _pad(text: str, size: int) -> str:
    """Prepend filler so a keyword starts at ~half the target size."""
    filler = ("lorem ipsum " * 2000)[: size // 2]
    return filler + text + filler


def test_extract_excerpt_finds_schedule_of_assessments():
    body = "Schedule of Assessments\nV1 Baseline Day 0 Vitals Labs ECG\nV2 Week 2 Day 14 Vitals Labs"
    text = _pad(body, 100_000)  # Force 'large' path so excerpt is used.
    excerpt = extract_relevant_excerpt(text)
    assert "Schedule of Assessments" in excerpt
    assert "V1 Baseline" in excerpt


def test_extract_excerpt_finds_inclusion_and_exclusion():
    body = (
        "Inclusion Criteria\nI1. Adults 18-75.\nI2. HbA1c between 7.0 and 10.5.\n\n"
        "Exclusion Criteria\nE1. Pregnancy.\nE2. HbA1c > 10.5."
    )
    text = _pad(body, 100_000)
    excerpt = extract_relevant_excerpt(text)
    assert "Inclusion Criteria" in excerpt
    assert "Exclusion Criteria" in excerpt
    assert "HbA1c" in excerpt


def test_extract_excerpt_is_case_insensitive():
    body = "VISIT SCHEDULE\nV1 Baseline\nELIGIBILITY CRITERIA\nI1. Adult."
    text = _pad(body, 100_000)
    excerpt = extract_relevant_excerpt(text)
    assert "VISIT SCHEDULE" in excerpt
    assert "ELIGIBILITY CRITERIA" in excerpt


def test_extract_excerpt_respects_max_chars():
    # Very long text with many section headers; excerpt should be capped.
    body = "\n".join(["Inclusion Criteria"] * 200)
    text = _pad(body, 500_000)
    excerpt = extract_relevant_excerpt(text, max_chars=10_000)
    assert len(excerpt) <= 10_000


def test_extract_excerpt_falls_back_to_leading_text_when_no_matches():
    text = "a" * 100_000  # No matches for any known section heading.
    excerpt = extract_relevant_excerpt(text, max_chars=5_000)
    assert excerpt == "a" * 5_000


def test_extract_excerpt_merges_overlapping_windows():
    # Two matches right next to each other should produce one window, not two.
    body = "Inclusion Criteria section body. Exclusion Criteria immediately follows."
    text = _pad(body, 100_000)
    excerpt = extract_relevant_excerpt(text)
    # Windows are merged, so the separator "---\n\n---" from concatenation
    # should appear 0 times (no gap between them after merging).
    assert excerpt.count("\n\n---\n\n") == 0
    assert "Inclusion Criteria" in excerpt
    assert "Exclusion Criteria" in excerpt


# ---------- parse_protocol_text large-input handling ----------

def test_parse_protocol_text_small_input_sends_full():
    """Under 40K chars → send full text (preserves existing behavior)."""
    expected = json.loads((FIX / "mini_protocol_spec.json").read_text())
    llm = StubLLM(expected)
    text = (FIX / "mini_protocol.txt").read_text()  # ~650 chars
    parse_protocol_text(text, llm=llm)
    assert llm.last_user == text


def test_parse_protocol_text_large_input_sends_only_excerpt():
    """Over 40K chars → send the excerpt, which is strictly smaller."""
    expected = json.loads((FIX / "mini_protocol_spec.json").read_text())
    llm = StubLLM(expected)
    # Build a >40K-char blob containing the keyword so excerpt returns something.
    body = "Inclusion Criteria\nI1. Adult with disease.\n" * 50
    filler = ("lorem ipsum " * 10000)  # ~120K chars of filler
    text = filler + body + filler
    parse_protocol_text(text, llm=llm)
    assert llm.last_user is not None
    assert len(llm.last_user) < len(text)
    assert "Inclusion Criteria" in llm.last_user
