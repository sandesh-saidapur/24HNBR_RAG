"""Model providers.

Text answers run on Groq (free tier, OpenAI-compatible API).
Photo reading (car identification) runs on Claude (vision).
Models can be overridden in the environment: TEXT_MODEL, VISION_MODEL, JUDGE_MODEL.
"""

from __future__ import annotations

import base64
import os
from typing import Protocol

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

DEFAULT_MODELS = {
    "text": "openai/gpt-oss-120b",  # Groq
    "vision": "claude-sonnet-5-5",  # Claude
    "judge": "claude-opus-5-5",  # Claude, offline evaluation only
}


def model_for(role: str) -> str:
    return os.environ.get(f"{role.upper()}_MODEL", DEFAULT_MODELS[role])


class TextLLM(Protocol):
    def complete(self, *, model: str, system: str, user: str, max_tokens: int) -> str: ...


class VisionLLM(Protocol):
    def describe_image(
        self,
        *,
        model: str,
        system: str,
        user: str,
        image: bytes,
        media_type: str,
        max_tokens: int,
    ) -> str: ...


class GroqClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None) -> None:
        self._key = api_key
        self._http = http or httpx.Client(timeout=60.0)

    def complete(self, *, model: str, system: str, user: str, max_tokens: int) -> str:
        response = self._http.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {self._key}"},
            json={
                "model": model,
                "max_tokens": max_tokens,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        response.raise_for_status()
        return str(response.json()["choices"][0]["message"]["content"])


class ClaudeClient:
    def __init__(self, api_key: str) -> None:
        import anthropic  # imported lazily so offline code never needs the SDK

        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, *, model: str, system: str, user: str, max_tokens: int) -> str:
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    def describe_image(
        self,
        *,
        model: str,
        system: str,
        user: str,
        image: bytes,
        media_type: str,
        max_tokens: int,
    ) -> str:
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.b64encode(image).decode("ascii"),
                            },
                        },
                        {"type": "text", "text": user},
                    ],
                }
            ],
        )
        return "".join(block.text for block in response.content if block.type == "text")


def get_text_llm() -> TextLLM | None:
    key = os.environ.get("GROQ_API_KEY")
    return GroqClient(key) if key else None


def get_vision_llm() -> VisionLLM | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    return ClaudeClient(key) if key else None
