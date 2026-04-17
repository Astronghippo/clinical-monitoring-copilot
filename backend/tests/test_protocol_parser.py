import json
from pathlib import Path

from app.services.protocol_parser import (
    ProtocolSpec,
    extract_text_from_pdf_bytes,
    parse_protocol_text,
)

FIX = Path(__file__).parent / "fixtures"


class StubLLM:
    def __init__(self, payload: dict):
        self._p = payload

    def json_completion(self, *, system, user, max_tokens=4096):
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
