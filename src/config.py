"""Central configuration, loaded once from environment variables / .env.

Everything tunable (provider, model, limits) lives here so nothing is
hard-coded in the agent logic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional; env vars still work without it.
    pass


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class Config:
    provider: str = os.getenv("LLM_PROVIDER", "mock").strip().lower()
    model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    request_timeout: int = int(os.getenv("LLM_TIMEOUT", "30"))
    max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "3"))

    max_steps: int = int(os.getenv("AGENT_MAX_STEPS", "5"))

    search_max_results: int = int(os.getenv("SEARCH_MAX_RESULTS", "3"))
    search_offline: bool = _bool("SEARCH_OFFLINE", False)

    @property
    def api_key(self) -> str | None:
        if self.provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        if self.provider == "groq":
            return os.getenv("GROQ_API_KEY")
        return os.getenv("OPENAI_API_KEY")

    @property
    def base_url(self) -> str | None:
        # Groq is OpenAI-compatible; only the base URL differs.
        if self.provider == "groq":
            return "https://api.groq.com/openai/v1"
        return None


config = Config()
