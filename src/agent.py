"""The healthcare agent: a small, explicit ReAct loop.

Flow per run:
    validate -> [ think -> search -> observe ]* -> final answer

The LLM emits one JSON step at a time (thought + action). We execute the tool,
feed the observation back, and repeat until it answers or we hit the step limit.
"""

from __future__ import annotations

import argparse
import json
import re

from pydantic import ValidationError

from src.config import config
from src.llm import LLMError, complete
from src.prompts import FEW_SHOT, SYSTEM_PROMPT
from src.schemas import Action, AgentResult, AgentStep
from src.tools import search_medical_database
from src.trace import Tracer

MAX_QUERY_CHARS = 500
DISCLAIMER = "This is general information, not a substitute for professional medical advice."


def validate_query(query: str) -> str:
    """Guard-rail: reject empty or oversized input before spending tokens."""
    query = (query or "").strip()
    if not query:
        raise ValueError("Query is empty. Please ask a health-related question.")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"Query is too long (max {MAX_QUERY_CHARS} characters).")
    return query


def _parse_step(raw: str) -> AgentStep:
    """Parse the LLM's reply into an AgentStep, tolerating stray prose."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM output.")
    return AgentStep.model_validate(json.loads(match.group(0)))


def run_agent(query: str, verbose: bool = True) -> AgentResult:
    query = validate_query(query)
    tracer = Tracer(query, verbose=verbose)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += FEW_SHOT
    messages.append({"role": "user", "content": f"Question: {query}"})

    last_observation = ""
    for step_num in range(1, config.max_steps + 1):
        try:
            raw = complete(messages)
            step = _parse_step(raw)
        except (LLMError, ValueError, ValidationError) as exc:
            tracer.note(f"Recovering from error: {exc}")
            return _fallback(query, last_observation, tracer, step_num)

        tracer.thought(step.thought)

        if step.action == Action.FINAL_ANSWER:
            answer = step.answer or DISCLAIMER
            tracer.final_answer(answer, step.sources)
            tracer.save()
            return AgentResult(
                query=query,
                answer=answer,
                sources=step.sources,
                steps_taken=step_num,
                trace=tracer.events,
            )

        # Otherwise: a search action.
        search_query = step.action_input or query
        tracer.tool_call(Action.SEARCH.value, search_query)
        last_observation = search_medical_database(search_query)
        tracer.observation(last_observation)

        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": f"Observation: {last_observation}"})

    # Step budget exhausted without a final answer.
    return _fallback(query, last_observation, tracer, config.max_steps)


def _fallback(query: str, observation: str, tracer: Tracer, steps: int) -> AgentResult:
    """Best-effort answer when the model errors out or runs out of steps."""
    sources: list[str] = []
    if observation:
        try:
            results = json.loads(observation)
            sources = [r["url"] for r in results]
            summary = " ".join(r["snippet"] for r in results[:2])
            answer = f"Here is what the sources suggest about '{query}': {summary} {DISCLAIMER}"
        except (json.JSONDecodeError, KeyError, TypeError):
            answer = f"I could not complete the reasoning reliably. {DISCLAIMER}"
    else:
        answer = f"I was unable to retrieve information for '{query}'. {DISCLAIMER}"

    tracer.note("Returning fallback answer.")
    tracer.final_answer(answer, sources)
    tracer.save()
    return AgentResult(
        query=query,
        answer=answer,
        sources=sources,
        steps_taken=steps,
        used_fallback=True,
        trace=tracer.events,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Healthcare Q&A agent")
    parser.add_argument("--domain", default="healthcare", help="Kept for assignment parity.")
    parser.add_argument("--query", required=True, help="The health question to answer.")
    args = parser.parse_args()

    try:
        result = run_agent(args.query)
    except ValueError as exc:
        raise SystemExit(f"Invalid query: {exc}")
    print("\n" + "=" * 60)
    print(result.answer)


if __name__ == "__main__":
    main()
