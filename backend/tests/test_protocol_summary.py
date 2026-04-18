"""Tests for the high-level protocol summarizer."""
from app.services.protocol_summary import summarize_protocol_text, summary_excerpt


class StubLLM:
    def __init__(self, payload: dict):
        self._p = payload
        self.last_user: str | None = None

    def json_completion(self, *, system, user, max_tokens=4096):
        self.last_user = user
        return self._p


# ---------- summary_excerpt ----------

def test_summary_excerpt_returns_whole_text_when_small():
    text = "short protocol body"
    assert summary_excerpt(text) == text


def test_summary_excerpt_truncates_long_text_to_max_chars():
    text = "x" * 200_000
    assert summary_excerpt(text, max_chars=1000) == "x" * 1000


# ---------- summarize_protocol_text ----------

def test_summarize_returns_normalized_shape():
    canned = {
        "study_id": "ACME-DM2-302",
        "title": "A Phase 2 Study of StudyDrug in Type 2 Diabetes",
        "short_description": "12-week study evaluating StudyDrug vs placebo in T2D.",
        "phase": "II",
        "indication": "Type 2 Diabetes",
        "sponsor": "ACME Pharma",
        "design": "randomized, double-blind, placebo-controlled",
        "arms": ["Arm A: StudyDrug", "Arm B: Placebo"],
        "primary_endpoint": "Change in HbA1c from baseline at Week 12",
        "secondary_endpoints": ["Fasting glucose", "Weight change"],
        "treatment_duration": "12 weeks",
        "sample_size": 200,
        "notable_aspects": "Standard Phase 2 design; no unusual features.",
    }
    llm = StubLLM(canned)
    out = summarize_protocol_text("any text", llm=llm)
    assert out["study_id"] == "ACME-DM2-302"
    assert out["phase"] == "II"
    assert out["arms"] == ["Arm A: StudyDrug", "Arm B: Placebo"]
    assert out["sample_size"] == 200


def test_summarize_normalizes_missing_fields_to_none():
    """If the LLM omits fields, they come back as None (not KeyError)."""
    llm = StubLLM({"title": "A minimal one"})
    out = summarize_protocol_text("any text", llm=llm)
    assert out["title"] == "A minimal one"
    assert out["phase"] is None
    assert out["indication"] is None
    assert out["arms"] == []
    assert out["secondary_endpoints"] == []
    assert out["sample_size"] is None


def test_summarize_converts_empty_strings_and_null_literals_to_none():
    llm = StubLLM({
        "title": "x",
        "phase": "",          # empty string from LLM
        "sponsor": "null",    # literal word
        "indication": None,
    })
    out = summarize_protocol_text("any text", llm=llm)
    assert out["phase"] is None
    assert out["sponsor"] is None
    assert out["indication"] is None


def test_summarize_only_sends_first_30k_chars_to_llm():
    """Summary excerpt is the leading portion — verify large inputs are trimmed."""
    llm = StubLLM({"title": "test"})
    long_text = ("SYNOPSIS SECTION \n" * 5000)  # ~90K chars
    summarize_protocol_text(long_text, llm=llm)
    assert llm.last_user is not None
    assert len(llm.last_user) <= 30_000
