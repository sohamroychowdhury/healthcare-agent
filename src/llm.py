"""Thin LLM layer.

One job: turn a list of chat messages into a string reply, with retries,
timeouts, and a graceful fallback. Providers sit behind a single function so
the agent never knows or cares which one is active.

A deterministic `mock` provider lets the whole project run and be graded with
no API key and no network.
"""

from __future__ import annotations

import json
import time
from typing import Dict, List

from src.config import config

Messages = List[Dict[str, str]]


class LLMError(Exception):
    """Raised when every retry against a real provider has failed."""


def complete(messages: Messages) -> str:
    """Return the model's reply text, retrying transient failures."""
    if config.provider == "mock":
        return _mock_complete(messages)

    last_error: Exception | None = None
    for attempt in range(1, config.max_retries + 1):
        try:
            return _provider_complete(messages)
        except Exception as exc:  # network/rate-limit/timeout -> back off and retry
            last_error = exc
            if attempt < config.max_retries:
                time.sleep(2 ** (attempt - 1))
    raise LLMError(f"LLM call failed after {config.max_retries} attempts: {last_error}")


def _provider_complete(messages: Messages) -> str:
    # OpenAI and Groq share the same SDK; Groq just points at a different URL.
    if config.provider in ("openai", "groq"):
        from openai import OpenAI

        client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.request_timeout,
        )
        resp = client.chat.completions.create(
            model=config.model,
            messages=messages,
            temperature=config.temperature,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""

    if config.provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=config.api_key, timeout=config.request_timeout)
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        chat = [m for m in messages if m["role"] != "system"]
        resp = client.messages.create(
            model=config.model,
            system=system,
            messages=chat,
            temperature=config.temperature,
            max_tokens=1024,
        )
        return resp.content[0].text

    raise LLMError(f"Unknown provider: {config.provider}")


def _mock_complete(messages: Messages) -> str:
    """A tiny rule-based stand-in for an LLM.

    It mimics the ReAct rhythm: search first, then answer once an Observation
    is present. Enough to drive the loop deterministically for demos/tests.
    """
    # Only look at the conversation after the real question, so the few-shot
    # example's Observation doesn't trick us into answering early.
    start = max(
        (i for i, m in enumerate(messages)
         if m["role"] == "user" and m["content"].startswith("Question:")),
        default=0,
    )
    live = messages[start:]
    user_query = live[0]["content"].replace("Question:", "").strip() if live else "your question"
    has_observation = any(
        m["role"] == "user" and m["content"].startswith("Observation:")
        for m in live
    )

    if not has_observation:
        return json.dumps({
            "thought": f"I should search the knowledge base about '{user_query}'.",
            "action": "search_medical_database",
            "action_input": user_query,
        })

    # Summarize whatever the latest observation returned.
    observation = next(
        m["content"] for m in reversed(live)
        if m["role"] == "user" and m["content"].startswith("Observation:")
    )
    results = json.loads(observation[len("Observation:"):].strip())
    snippets = " ".join(r["snippet"] for r in results[:2])
    sources = [r["url"] for r in results]
    answer = (
        f"Based on the sources, here is what I found about {user_query}: {snippets} "
        "This is general information, not a substitute for professional medical advice."
    )
    return json.dumps({
        "thought": "I have enough evidence from the search to answer.",
        "action": "final_answer",
        "answer": answer,
        "sources": sources,
    })
