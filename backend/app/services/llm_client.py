from __future__ import annotations

import json
import re
from typing import Any

from anthropic import Anthropic

from app.config import settings

# Strips a leading ```json or ``` fence and a trailing ``` fence.
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
# Finds the first {...} object OR [...] array in a string (greedy to the last brace).
# Claude sometimes emits "Here is the JSON: {...}" despite instructions — this rescues it.
_JSON_BLOCK = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


class LLMClient:
    """Thin wrapper over the Anthropic SDK.

    Keeps call sites terse and centralizes JSON parsing (incl. stripping
    markdown code fences that Claude sometimes emits even when told not to).
    """

    def __init__(
        self,
        anthropic_client: Any | None = None,
        model: str | None = None,
    ) -> None:
        self._client = anthropic_client or Anthropic(api_key=settings.anthropic_api_key)
        self._model = model or settings.claude_model

    def json_completion(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
    ) -> dict:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = msg.content[0].text
        cleaned = _FENCE.sub("", text).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback: Claude wrapped the JSON in prose (e.g. "Here is the result: {...}").
            # Extract the first JSON object/array and try again.
            match = _JSON_BLOCK.search(cleaned)
            if match is None:
                raise
            return json.loads(match.group(1))

    def text_completion(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 2048,
    ) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text
