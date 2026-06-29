"""Reasoning-trace recorder.

Captures every step of a run (thoughts, tool calls, observations, final answer)
so the full chain is inspectable in the console and saved to a JSONL file.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

TRACES_DIR = Path(__file__).resolve().parents[1] / "traces"


class Tracer:
    def __init__(self, query: str, verbose: bool = True):
        self.query = query
        self.verbose = verbose
        self.events: List[Dict[str, Any]] = []
        self._log("query", {"text": query})

    def thought(self, text: str) -> None:
        self._log("thought", {"text": text})

    def tool_call(self, name: str, arg: str) -> None:
        self._log("tool_call", {"tool": name, "input": arg})

    def observation(self, content: str) -> None:
        self._log("observation", {"content": content})

    def final_answer(self, answer: str, sources: List[str]) -> None:
        self._log("final_answer", {"answer": answer, "sources": sources})

    def note(self, text: str) -> None:
        self._log("note", {"text": text})

    def _log(self, kind: str, payload: Dict[str, Any]) -> None:
        event = {"kind": kind, **payload}
        self.events.append(event)
        if self.verbose:
            self._print(kind, payload)

    @staticmethod
    def _print(kind: str, payload: Dict[str, Any]) -> None:
        labels = {
            "query": "QUERY",
            "thought": "THOUGHT",
            "tool_call": "ACTION",
            "observation": "OBSERVATION",
            "final_answer": "ANSWER",
            "note": "NOTE",
        }
        label = labels.get(kind, kind.upper())
        if kind == "tool_call":
            print(f"[{label}] {payload['tool']}({payload['input']!r})")
        elif kind == "observation":
            preview = payload["content"].replace("\n", " ")
            print(f"[{label}] {preview[:160]}{'...' if len(preview) > 160 else ''}")
        elif kind == "final_answer":
            print(f"[{label}] {payload['answer']}")
            if payload["sources"]:
                print(f"[SOURCES] {', '.join(payload['sources'])}")
        else:
            print(f"[{label}] {payload.get('text', '')}")

    def save(self) -> Path:
        TRACES_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = TRACES_DIR / f"trace-{stamp}.jsonl"
        with path.open("w") as f:
            for event in self.events:
                f.write(json.dumps(event) + "\n")
        return path
