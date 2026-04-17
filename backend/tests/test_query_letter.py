import json
from datetime import date

from app.services.query_letter import draft_query_letter


class StubLLM:
    def __init__(self, payload: dict):
        self._payload = payload
        self.last_user = None
        self.last_system = None

    def json_completion(self, *, system, user, max_tokens=4096):
        self.last_system = system
        self.last_user = user
        return self._payload


def _finding():
    return {
        "analyzer": "completeness",
        "severity": "major",
        "subject_id": "1007",
        "summary": "Subject 1007 V2 missing required: Labs",
        "detail": "No Labs testcodes captured at Week 2 visit.",
        "protocol_citation": "Schedule of Assessments, visit V2",
        "data_citation": {"domain": "VS", "usubjid": "1007", "visit": "Week 2"},
    }


def test_draft_query_letter_returns_shape():
    stub_resp = {
        "subject_line": "Data Query — ACME-DM2-302 — Subject 1007 — Missing labs at V2",
        "body": "Dear Site 01 Investigator, …",
        "reply_by": "2025-06-22",
    }
    llm = StubLLM(stub_resp)
    letter = draft_query_letter(
        study_id="ACME-DM2-302",
        site_id="SITE01",
        finding=_finding(),
        today=date(2025, 6, 15),
        llm=llm,
    )
    assert letter["subject_line"].startswith("Data Query")
    assert "1007" in letter["subject_line"]
    assert letter["body"].startswith("Dear Site 01")
    assert letter["reply_by"] == "2025-06-22"


def test_draft_query_letter_passes_finding_to_llm():
    llm = StubLLM({"subject_line": "x", "body": "y", "reply_by": "2025-06-22"})
    draft_query_letter(
        study_id="ACME-DM2-302",
        site_id="SITE01",
        finding=_finding(),
        today=date(2025, 6, 15),
        llm=llm,
    )
    payload = json.loads(llm.last_user)
    assert payload["study_id"] == "ACME-DM2-302"
    assert payload["site_id"] == "SITE01"
    assert payload["today_iso"] == "2025-06-15"
    assert payload["finding"]["subject_id"] == "1007"


def test_draft_query_letter_supplies_defaults_for_missing_fields():
    # If LLM response omits a key, the helper fills with "".
    llm = StubLLM({"subject_line": "hi"})
    letter = draft_query_letter(
        study_id="X", site_id="S",
        finding=_finding(), today=date(2025, 1, 1), llm=llm,
    )
    assert letter["subject_line"] == "hi"
    assert letter["body"] == ""
    assert letter["reply_by"] == ""
