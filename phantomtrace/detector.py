"""Rule-based anomaly detection. Fast, deterministic, no model needed."""
from __future__ import annotations

import re
import statistics

from .models import SEVERITY_ORDER, Anomaly, Event

SECRET_PATTERNS = {
    "API key (sk-...)": re.compile(r"sk-[A-Za-z0-9]{16,}"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Bearer token": re.compile(r"Bearer\s+[A-Za-z0-9\-_.=]{20,}"),
    "Password in text": re.compile(r"(?i)password\s*[=:]\s*\S{4,}"),
}

SLOW_FLOOR_MS = 5000
LOOP_THRESHOLD = 3


def _short(text: str | None, n: int = 80) -> str:
    text = (text or "").replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


def detect_errors(events: list[Event]) -> list[Anomaly]:
    return [
        Anomaly(
            step=e.step,
            rule="error",
            severity="high",
            title=f"Error in {e.tool or e.event_type}",
            detail=_short(e.output or e.input, 200) or "Event flagged as an error.",
        )
        for e in events
        if e.status.lower() == "error" or e.event_type.lower() == "error"
    ]


def detect_loops(events: list[Event]) -> list[Anomaly]:
    found: list[Anomaly] = []
    calls = [e for e in events if e.event_type == "tool_call"]
    streak: list[Event] = []
    for e in calls:
        if streak and (e.tool, e.input) == (streak[0].tool, streak[0].input):
            streak.append(e)
        else:
            streak = [e]
        if len(streak) == LOOP_THRESHOLD:  # report once per streak
            found.append(
                Anomaly(
                    step=e.step,
                    rule="loop",
                    severity="high",
                    title=f"Possible loop: '{e.tool}' repeated",
                    detail=f"Same call with identical input {LOOP_THRESHOLD}+ times in a row: {_short(e.input)}",
                )
            )
    return found


def detect_slow(events: list[Event]) -> list[Anomaly]:
    lat = [e.latency_ms for e in events if e.latency_ms is not None]
    if not lat:
        return []
    limit = SLOW_FLOOR_MS
    if len(lat) >= 5:
        limit = max(SLOW_FLOOR_MS, statistics.mean(lat) + 2 * statistics.pstdev(lat))
    return [
        Anomaly(
            step=e.step,
            rule="slow",
            severity="medium",
            title=f"Slow step: {e.tool or e.event_type}",
            detail=f"{e.latency_ms:.0f} ms (threshold {limit:.0f} ms).",
        )
        for e in events
        if e.latency_ms is not None and e.latency_ms > limit
    ]


def detect_empty_results(events: list[Event]) -> list[Anomaly]:
    return [
        Anomaly(
            step=e.step,
            rule="empty_result",
            severity="medium",
            title=f"Empty result from {e.tool or 'tool'}",
            detail="Tool returned nothing; the agent may continue on bad assumptions.",
        )
        for e in events
        if e.event_type == "tool_result" and not (e.output or "").strip() and e.status.lower() != "error"
    ]


def detect_token_spikes(events: list[Event]) -> list[Anomaly]:
    toks = [e.tokens for e in events if e.tokens]
    if len(toks) < 4:
        return []
    med = statistics.median(toks)
    return [
        Anomaly(
            step=e.step,
            rule="token_spike",
            severity="low",
            title="Token spike",
            detail=f"{e.tokens} tokens vs median {med:.0f}.",
        )
        for e in events
        if e.tokens and e.tokens > max(1000, 3 * med)
    ]


def detect_secrets(events: list[Event]) -> list[Anomaly]:
    found: list[Anomaly] = []
    for e in events:
        blob = f"{e.input or ''}\n{e.output or ''}"
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(blob):
                found.append(
                    Anomaly(
                        step=e.step,
                        rule="secret_leak",
                        severity="critical",
                        title=f"Possible secret in log: {label}",
                        detail="Sensitive-looking value appears in the agent trace. Redact before sharing logs.",
                    )
                )
    return found


def detect_missing_final(events: list[Event]) -> list[Anomaly]:
    if events and not any(e.event_type == "final" for e in events):
        return [
            Anomaly(
                step=events[-1].step,
                rule="no_final",
                severity="medium",
                title="Run never produced a final answer",
                detail="The trace ends without a 'final' event. The agent may have crashed or been cut off.",
            )
        ]
    return []


DETECTORS = (
    detect_errors,
    detect_loops,
    detect_slow,
    detect_empty_results,
    detect_token_spikes,
    detect_secrets,
    detect_missing_final,
)


def analyze(events: list[Event]) -> list[Anomaly]:
    found: list[Anomaly] = []
    for detector in DETECTORS:
        found.extend(detector(events))
    found.sort(key=lambda a: (-SEVERITY_ORDER[a.severity], a.step))
    return found
