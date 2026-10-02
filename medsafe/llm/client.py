from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_ALLOWLIST = frozenset({"GROQ_API_KEY", "MEDSAFE_LLM_PROVIDER", "MEDSAFE_LLM_MODEL"})
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_REQUEST_CAP = 80
_groq_request_count = 0
_groq_budget_lock = threading.Lock()
_env_load_lock = threading.Lock()
_env_loaded = False


class ProviderError(RuntimeError):
    """Fixed, credential-free provider failure."""


class EnvFileError(ValueError):
    """Fixed, content-free .env parse failure."""


def parse_env_file(path: Path) -> dict[str, str]:
    """Read a bounded allowlisted KEY=VALUE file; errors never include file contents."""
    try:
        if path.stat().st_size > 16 * 1024:
            raise EnvFileError("Environment file exceeds the size limit.")
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except EnvFileError:
        raise
    except (OSError, UnicodeError):
        raise EnvFileError("Environment file could not be read.") from None
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise EnvFileError("Environment file has invalid syntax.")
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            raise EnvFileError("Environment file has invalid syntax.")
        if key not in ENV_ALLOWLIST:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        parsed[key] = value
    return parsed


def _load_project_env() -> None:
    global _env_loaded
    if os.getenv("MEDSAFE_DISABLE_DOTENV") == "1":
        return
    with _env_load_lock:
        if _env_loaded:
            return
        try:
            values = parse_env_file(PROJECT_ROOT / ".env")
        except EnvFileError:
            values = {}
        for key, value in values.items():
            os.environ.setdefault(key, value)
        _env_loaded = True


@dataclass
class LlmConfig:
    enabled: bool
    api_key: str | None = field(repr=False)
    model: str | None
    provider: str = "anthropic"

    def __str__(self) -> str:
        key_state = "configured" if self.api_key else "not configured"
        return (f"LlmConfig(enabled={self.enabled}, provider={self.provider}, "
                f"model={self.model or 'not configured'}, api_key={key_state})")

    @classmethod
    def from_env(cls) -> "LlmConfig":
        _load_project_env()
        provider = os.getenv("MEDSAFE_LLM_PROVIDER", "anthropic").strip().casefold()
        enabled = os.getenv("MEDSAFE_LLM_ENABLED", "false").casefold() in {"1", "true", "yes"}
        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            model = os.getenv("MEDSAFE_LLM_MODEL")
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            model = os.getenv("MEDSAFE_LLM_MODEL")
        return cls(enabled=enabled, api_key=api_key, model=model, provider=provider)


class AnthropicClient:
    """Small injectable provider adapter; never logs prompts, outputs, or credentials."""
    def __init__(self, config: LlmConfig):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=config.api_key, timeout=10.0, max_retries=1)
        self.model = config.model

    def complete(self, system: str, prompt: str) -> str:
        response = self.client.messages.create(model=self.model, max_tokens=400,
            temperature=0, system=system, messages=[{"role": "user", "content": prompt}])
        return "".join(block.text for block in response.content if getattr(block, "type", None) == "text")


def reset_groq_request_budget() -> None:
    global _groq_request_count
    with _groq_budget_lock:
        _groq_request_count = 0


def _claim_groq_request() -> bool:
    global _groq_request_count
    with _groq_budget_lock:
        if _groq_request_count >= GROQ_REQUEST_CAP:
            return False
        _groq_request_count += 1
        return True


class GroqClient:
    """OpenAI-compatible Groq Chat Completions adapter using urllib only."""
    def __init__(self, config: LlmConfig, timeout: float = 10.0):
        if not config.api_key or not config.model:
            raise ProviderError("Groq provider is not configured.")
        self._api_key = config.api_key
        self._model = config.model
        self._timeout = timeout

    def complete(self, system: str, prompt: str) -> str:
        payload = json.dumps({
            "model": self._model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": prompt}],
            "temperature": 0,
            "max_completion_tokens": 800,
            "stream": False,
        }).encode("utf-8")
        if self._model.startswith("openai/gpt-oss-"):
            request_payload = json.loads(payload)
            request_payload["reasoning_effort"] = "low"
            if "json" in system.casefold():
                request_payload["response_format"] = {"type": "json_object"}
            payload = json.dumps(request_payload).encode("utf-8")
        for attempt in range(2):
            if not _claim_groq_request():
                raise ProviderError("Provider request limit reached.")
            request = urllib.request.Request(GROQ_CHAT_URL, data=payload,
                headers={"Authorization": f"Bearer {self._api_key}",
                         "Content-Type": "application/json",
                         "User-Agent": "MedSafe/0.1.0"}, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise ProviderError("Provider returned an invalid response.")
                return content
            except urllib.error.HTTPError as error:
                transient = error.code == 429 or 500 <= error.code <= 599
                if transient and attempt == 0:
                    continue
                raise ProviderError("Provider request failed.") from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == 0:
                    continue
                raise ProviderError("Provider request failed.") from None
            except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                raise ProviderError("Provider returned an invalid response.") from None
        raise ProviderError("Provider request failed.")


def provider_client(config: LlmConfig) -> Any:
    if config.provider == "groq":
        return GroqClient(config)
    return AnthropicClient(config)


def readiness(config: LlmConfig, requested: bool) -> tuple[str, str]:
    if not requested:
        return "DISABLED", "Per-request use_llm flag is off."
    if not config.enabled:
        return "DISABLED", "MEDSAFE_LLM_ENABLED is off."
    if config.provider not in {"anthropic", "groq"}:
        return "DISABLED", "MEDSAFE_LLM_PROVIDER is unsupported."
    if not config.model:
        return "DISABLED", "MEDSAFE_LLM_MODEL is not configured."
    if not config.api_key:
        key_name = "GROQ_API_KEY" if config.provider == "groq" else "ANTHROPIC_API_KEY"
        return "NOT_AVAILABLE", f"{key_name} is not configured."
    if config.provider == "anthropic":
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return "NOT_AVAILABLE", "Optional anthropic SDK is not installed."
    return "ENABLED", "LLM provider configured; guarded features enabled."
