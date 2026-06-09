from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class LLMClient(Protocol):
    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.0) -> str:
        ...


@dataclass
class OfflineClient:
    """A no-network client used for examples and tests."""

    response: str = ""

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.0) -> str:
        return self.response


@dataclass
class OpenAICompatibleClient:
    """Minimal OpenAI-compatible chat-completions client.

    Works with OpenAI, DeepSeek, Qwen-compatible gateways, vLLM OpenAI
    servers, and similar providers. No SDK dependency is required.
    """

    model: str
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    timeout: int = 120

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.0) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        try:
            return body["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected chat completion response: {body}") from exc


def make_client(
    provider: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key_env: str | None = None,
    timeout: int = 120,
) -> LLMClient:
    provider = provider.lower()
    if provider in {"offline", "none", "heuristic"}:
        return OfflineClient()

    defaults = {
        "openai": ("OPENAI_API_KEY", "https://api.openai.com/v1"),
        "deepseek": ("DEEPSEEK_API_KEY", "https://api.deepseek.com/v1"),
        "qwen": ("DASHSCOPE_API_KEY", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "vllm": ("VLLM_API_KEY", "http://127.0.0.1:8000/v1"),
    }
    if provider not in defaults:
        raise ValueError(f"Unknown provider: {provider}")
    default_env, default_url = defaults[provider]
    env_name = api_key_env or default_env
    api_key = os.environ.get(env_name)
    if not api_key:
        raise RuntimeError(f"Missing API key in environment variable {env_name}")
    if not model:
        raise RuntimeError("--model is required for online LLM providers")
    return OpenAICompatibleClient(
        model=model,
        api_key=api_key,
        base_url=base_url or default_url,
        timeout=timeout,
    )

