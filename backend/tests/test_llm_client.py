import json

import pytest

from app.services.llm_client import LLMClient, _extract_balanced_json


class FakeClient:
    """Single-response fake. Returns the same payload for every call."""

    def __init__(self, payload: str):
        self._payload = payload
        self.messages = self
        self.call_count = 0

    def create(self, **kwargs):
        self.call_count += 1

        class M:
            def __init__(self, text):
                self.content = [type("B", (), {"text": text})()]

        return M(self._payload)


class SequenceClient:
    """Returns a different payload on each successive call."""

    def __init__(self, payloads: list[str]):
        self._payloads = list(payloads)
        self.messages = self
        self.call_count = 0

    def create(self, **kwargs):
        text = self._payloads[self.call_count]
        self.call_count += 1

        class M:
            def __init__(self, text):
                self.content = [type("B", (), {"text": text})()]

        return M(text)


# ---------- Basic parsing ----------

def test_json_completion_parses_object():
    fake = FakeClient('{"ok": true, "count": 3}')
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    assert llm.json_completion(system="x", user="y") == {"ok": True, "count": 3}


def test_json_completion_strips_markdown_fence():
    fake = FakeClient('```json\n{"a":1}\n```')
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    assert llm.json_completion(system="x", user="y") == {"a": 1}


def test_json_completion_strips_plain_fence():
    fake = FakeClient('```\n{"b":2}\n```')
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    assert llm.json_completion(system="x", user="y") == {"b": 2}


def test_text_completion_returns_raw_text():
    fake = FakeClient("Hello, Claude.")
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    assert llm.text_completion(system="x", user="y") == "Hello, Claude."


# ---------- Prose-wrapped JSON ----------

def test_json_completion_extracts_from_prose_wrapper():
    fake = FakeClient(
        'Sure, here is the result:\n{"missing": ["ECG"], "reasoning": "no ECG captured"}\n\nLet me know.'
    )
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    assert llm.json_completion(system="x", user="y") == {
        "missing": ["ECG"],
        "reasoning": "no ECG captured",
    }


def test_json_completion_extracts_array_from_prose():
    fake = FakeClient('Here you go: [{"a": 1}, {"a": 2}] — hope that helps!')
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    assert llm.json_completion(system="x", user="y") == [{"a": 1}, {"a": 2}]


# ---------- Balanced-bracket walker unit tests ----------

def test_extract_balanced_handles_nested_objects():
    text = 'Prose { "a": {"nested": {"deep": 1}}, "b": [1,2,3] } more prose'
    got = _extract_balanced_json(text)
    assert got is not None
    parsed = json.loads(got)
    assert parsed["a"]["nested"]["deep"] == 1
    assert parsed["b"] == [1, 2, 3]


def test_extract_balanced_tolerates_braces_in_strings():
    text = 'Result: {"note": "this } has { curly braces } inside", "ok": true}'
    got = _extract_balanced_json(text)
    assert got is not None
    parsed = json.loads(got)
    assert parsed["note"] == "this } has { curly braces } inside"
    assert parsed["ok"] is True


def test_extract_balanced_handles_escaped_quotes_in_strings():
    text = 'Here: {"msg": "she said \\"hi\\"", "n": 1} (done)'
    got = _extract_balanced_json(text)
    assert got is not None
    parsed = json.loads(got)
    assert parsed["msg"] == 'she said "hi"'


def test_extract_balanced_returns_none_when_no_json():
    assert _extract_balanced_json("no json here, sorry") is None


def test_extract_balanced_picks_first_of_multiple_blocks():
    """When response contains multiple { ... }, we take the first one (not greedy-to-last)."""
    text = '{"first": 1} and {"second": 2}'
    got = _extract_balanced_json(text)
    assert got is not None
    assert json.loads(got) == {"first": 1}


# ---------- Retry on first-response failure ----------

def test_json_completion_retries_on_unparseable_and_succeeds():
    # First call returns completely unparseable prose; retry returns valid JSON.
    fake = SequenceClient(
        ["Sorry I cannot help with that.", '{"status": "ok"}']
    )
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    out = llm.json_completion(system="x", user="y")
    assert out == {"status": "ok"}
    assert fake.call_count == 2


def test_json_completion_raises_after_retry_exhausted():
    fake = SequenceClient(["still not JSON", "still not JSON either"])
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    with pytest.raises(json.JSONDecodeError) as excinfo:
        llm.json_completion(system="x", user="y")
    assert "after retry" in str(excinfo.value)
    assert fake.call_count == 2  # First + one retry


def test_json_completion_does_not_retry_if_first_parses():
    fake = SequenceClient(['{"ok": true}'])
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    out = llm.json_completion(system="x", user="y")
    assert out == {"ok": True}
    assert fake.call_count == 1
