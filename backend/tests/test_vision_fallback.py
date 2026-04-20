"""Tests for Claude Vision PDF fallback when pypdf produces poor text extraction.

Strategy: parse_protocol_pdf_bytes(data, llm, vision_llm) is a new function that:
1. Tries pypdf text extraction.
2. If extracted text is too short (< MIN_TEXT_CHARS), falls back to
   vision_llm.pdf_text_extraction(data) to get richer text.
3. Passes whichever text it has to the normal parse_protocol_text() path.
"""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


def _mini_spec() -> dict:
    return json.loads((FIX / "mini_protocol_spec.json").read_text())


# ------------------------------------------------------------------ helpers

class StubParseLLM:
    """Stub for the JSON-completion LLM used in parse_protocol_text."""
    def __init__(self, payload: dict):
        self._payload = payload
        self.last_user: str | None = None

    def json_completion(self, *, system, user, max_tokens=16000):
        self.last_user = user
        return self._payload


class StubVisionLLM:
    """Stub for the vision LLM used to extract text from PDF bytes."""
    def __init__(self, extracted_text: str = "Inclusion Criteria\nI1. Adult."):
        self._text = extracted_text
        self.called_with_bytes: bytes | None = None

    def pdf_text_extraction(self, pdf_bytes: bytes) -> str:
        self.called_with_bytes = pdf_bytes
        return self._text


def _make_minimal_pdf() -> bytes:
    """Create a minimal valid PDF with no readable text (simulates scanned doc)."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_text_pdf(text: str) -> bytes:
    """Create a PDF containing readable text."""
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf)
    for i, line in enumerate(text.splitlines()):
        c.drawString(50, 750 - i * 15, line)
    c.save()
    buf.seek(0)
    return buf.read()


# ------------------------------------------------------------------ unit tests

def test_parse_pdf_bytes_uses_pypdf_when_text_is_sufficient():
    """When pypdf extracts enough text, vision fallback is NOT called."""
    from app.services.protocol_parser import parse_protocol_pdf_bytes

    # PDF with lots of text
    rich_text = (
        "Inclusion Criteria\n" + "I1. Adult with HbA1c >= 7.0.\n" * 60
    )
    pdf_bytes = _make_text_pdf(rich_text)

    parse_llm = StubParseLLM(_mini_spec())
    vision_llm = StubVisionLLM()

    parse_protocol_pdf_bytes(pdf_bytes, llm=parse_llm, vision_llm=vision_llm)

    assert vision_llm.called_with_bytes is None  # Vision NOT invoked


def test_parse_pdf_bytes_triggers_vision_fallback_on_sparse_text():
    """When pypdf extracts < threshold chars, vision_llm.pdf_text_extraction is called."""
    from app.services.protocol_parser import parse_protocol_pdf_bytes

    sparse_pdf = _make_minimal_pdf()  # blank page → near-zero text
    parse_llm = StubParseLLM(_mini_spec())
    vision_llm = StubVisionLLM("Inclusion Criteria\nI1. Adult.\nVisit Schedule\nV1 Baseline.")

    parse_protocol_pdf_bytes(sparse_pdf, llm=parse_llm, vision_llm=vision_llm)

    assert vision_llm.called_with_bytes == sparse_pdf


def test_parse_pdf_bytes_passes_vision_text_to_parse_llm():
    """After vision extraction the text is forwarded to the JSON-completion LLM."""
    from app.services.protocol_parser import parse_protocol_pdf_bytes

    sparse_pdf = _make_minimal_pdf()
    rich_vision_text = "Inclusion Criteria\nI1. HbA1c test.\nExclusion Criteria\nE1. Pregnancy.\n" * 20
    parse_llm = StubParseLLM(_mini_spec())
    vision_llm = StubVisionLLM(rich_vision_text)

    parse_protocol_pdf_bytes(sparse_pdf, llm=parse_llm, vision_llm=vision_llm)

    assert parse_llm.last_user is not None
    assert "Inclusion Criteria" in parse_llm.last_user


def test_parse_pdf_bytes_returns_protocol_spec():
    """Result should be a ProtocolSpec regardless of which path was taken."""
    from app.services.protocol_parser import ProtocolSpec, parse_protocol_pdf_bytes

    sparse_pdf = _make_minimal_pdf()
    parse_llm = StubParseLLM(_mini_spec())
    vision_llm = StubVisionLLM("Inclusion Criteria\nI1. Adult.\n" * 30)

    spec = parse_protocol_pdf_bytes(sparse_pdf, llm=parse_llm, vision_llm=vision_llm)

    assert isinstance(spec, ProtocolSpec)
    assert spec.study_id == "ACME-DM2-302"


def test_parse_pdf_bytes_works_without_vision_llm_if_text_sufficient():
    """vision_llm defaults to None; no error if text is sufficient."""
    from app.services.protocol_parser import parse_protocol_pdf_bytes

    rich_text = "Inclusion Criteria\n" + "I1. Adult.\n" * 60
    pdf_bytes = _make_text_pdf(rich_text)
    parse_llm = StubParseLLM(_mini_spec())

    # Should not raise even with no vision_llm
    spec = parse_protocol_pdf_bytes(pdf_bytes, llm=parse_llm, vision_llm=None)
    from app.services.protocol_parser import ProtocolSpec
    assert isinstance(spec, ProtocolSpec)


# ------------------------------------------------------------------ LLMClient.pdf_text_extraction

def test_llm_client_pdf_text_extraction_method_exists():
    """LLMClient must expose pdf_text_extraction(pdf_bytes) -> str."""
    from app.services.llm_client import LLMClient
    assert hasattr(LLMClient, "pdf_text_extraction"), (
        "LLMClient must have a pdf_text_extraction method for vision fallback"
    )


def test_llm_client_pdf_text_extraction_calls_anthropic_with_document_block():
    """pdf_text_extraction should pass a document content block to the Anthropic API."""
    import base64
    from app.services.llm_client import LLMClient

    dummy_pdf = b"%PDF-1.4 fake"

    class MockClient:
        def __init__(self):
            self.messages = self

        def create(self, **kwargs):
            self._last_call = kwargs

            class _Msg:
                content = [type("_C", (), {"text": "extracted text from PDF"})()]
            return _Msg()

    mock = MockClient()
    client = LLMClient(anthropic_client=mock)
    result = client.pdf_text_extraction(dummy_pdf)

    assert result == "extracted text from PDF"
    messages = mock._last_call["messages"]
    assert len(messages) == 1
    content = messages[0]["content"]
    # Must contain a document block with the PDF bytes
    doc_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "document"]
    assert len(doc_blocks) == 1
    source = doc_blocks[0]["source"]
    assert source["media_type"] == "application/pdf"
    assert base64.b64decode(source["data"]) == dummy_pdf
