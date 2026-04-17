from app.services.llm_client import LLMClient


class FakeClient:
    def __init__(self, payload: str):
        self._payload = payload
        self.messages = self

    def create(self, **kwargs):
        class M:
            def __init__(self, text):
                self.content = [type("B", (), {"text": text})()]
        return M(self._payload)


def test_json_completion_parses_object():
    fake = FakeClient('{"ok": true, "count": 3}')
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    out = llm.json_completion(system="be json", user="data")
    assert out == {"ok": True, "count": 3}


def test_json_completion_strips_markdown_fence():
    fake = FakeClient("```json\n{\"a\":1}\n```")
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    assert llm.json_completion(system="x", user="y") == {"a": 1}


def test_json_completion_strips_plain_fence():
    # Also handle the generic ``` ... ``` case without 'json' tag
    fake = FakeClient("```\n{\"b\":2}\n```")
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    assert llm.json_completion(system="x", user="y") == {"b": 2}


def test_text_completion_returns_raw_text():
    fake = FakeClient("Hello, Claude.")
    llm = LLMClient(anthropic_client=fake, model="claude-sonnet-4-6")
    assert llm.text_completion(system="x", user="y") == "Hello, Claude."
