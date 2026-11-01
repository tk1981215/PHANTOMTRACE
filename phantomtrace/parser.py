from __future__ import annotations

import json

from .models import Event

_ALIASES = (
    ("type", "event_type"),
    ("event", "event_type"),
    ("ts", "timestamp"),
    ("time", "timestamp"),
    ("latency", "latency_ms"),
    ("args", "input"),
    ("result", "output"),
)


def parse_jsonl(text: str) -> tuple[list[Event], list[str]]:
    """Parse JSON-lines agent logs. Returns (events, problems). Bad lines are skipped, never fatal."""
    events: list[Event] = []
    problems: list[str] = []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("line is not a JSON object")
            for alias, key in _ALIASES:
                if alias in obj and key not in obj:
                    obj[key] = obj.pop(alias)
            obj.setdefault("step", len(events) + 1)
            events.append(Event.model_validate(obj))
        except ValueError as exc:  # JSONDecodeError and pydantic ValidationError both subclass ValueError
            problems.append(f"line {n}: {str(exc).splitlines()[0]}")
    events.sort(key=lambda e: e.step)
    return events, problems
