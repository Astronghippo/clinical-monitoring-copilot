from __future__ import annotations

import json
import re
from typing import Any

from anthropic import Anthropic

from app.config import settings

# Strips a leading ```json or ``` fence and a trailing ``` fence.
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_balanced_json(text: str) -> str | None:
    """Find the first balanced JSON object or array in `text`.

    Walks character-by-character, respecting string literals and escape chars,
    so nested braces and braces inside strings don't confuse it. Returns the
    JSON substring, or None if nothing found.
    """
    open_chars = {"{": "}", "[": "]"}
    # Find the first opening bracket outside a string.
    start = -1
    for i, c in enumerate(text):
        if c in open_chars:
            start = i
            break
    if start < 0:
        return None

    opener = text[start]
    closer = open_chars[opener]
    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


class LLMClient:
    """Thin wrapper over the Anthropic SDK.

    Centralizes JSON parsing with three layers of resilience:
    1. Try strict json.loads on the raw (de-fenced) response.
    2. If that fails, extract the first balanced JSON object/array and parse that.
    3. If that also fails, retry the API call once with a stronger "JSON only" reminder.
    """

    def __init__(
        self,
        anthropic_client: Any | None = None,
        model: str | None = None,
    ) -> None:
        # max_retries=8 so rate-limit bursts (429s) are tolerated silently via
        # the SDK's exponential backoff. Default is 2, which isn't enough when
        # analyzers fire many requests in rapid succession.
        self._client = anthropic_client or Anthropic(
            api_key=settings.anthropic_api_key,
            max_retries=8,
        )
        self._model = model or settings.claude_model

    def _call(self, *, system: str, user: str, max_tokens: int) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text

    def _parse_json_lenient(self, text: str):
        """Try strict parse, then balanced-bracket extraction. Raise if neither works."""
        cleaned = _FENCE.sub("", text).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            extracted = _extract_balanced_json(cleaned)
            if extracted is None:
                raise
            return json.loads(extracted)

    def json_completion(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
    ) -> Any:
        """Get Claude to return JSON, tolerating prose wrappers and retrying once."""
        text = self._call(system=system, user=user, max_tokens=max_tokens)
        try:
            return self._parse_json_lenient(text)
        except json.JSONDecodeError as first_err:
            # Retry once with a stronger instruction before giving up.
            retry_system = (
                system
                + "\n\nCRITICAL: Your previous reply was not valid JSON. "
                "Reply with ONLY a single JSON value. No prose before or after. "
                "No markdown. No code fence. Just JSON."
            )
            retry_text = self._call(
                system=retry_system, user=user, max_tokens=max_tokens
            )
            try:
                return self._parse_json_lenient(retry_text)
            except json.JSONDecodeError:
                # Give up, surface the original error with some context.
                preview = (text[:500] + "…") if len(text) > 500 else text
                raise json.JSONDecodeError(
                    f"LLM returned non-JSON after retry. First response preview: {preview!r}",
                    first_err.doc,
                    first_err.pos,
                ) from first_err

    def text_completion(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 2048,
    ) -> str:
        return self._call(system=system, user=user, max_tokens=max_tokens)

    def chat_completion(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int = 1024,
    ) -> str:
        """Multi-turn chat completion.

        `messages` is a list of ``{"role": "user"|"assistant", "content": "…"}``
        dicts.  Returns the assistant's reply as a plain string.
        """
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return msg.content[0].text
