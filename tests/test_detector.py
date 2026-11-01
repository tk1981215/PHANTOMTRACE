import json

from phantomtrace.detector import analyze
from phantomtrace.parser import parse_jsonl


def _rules(path):
    events, problems = parse_jsonl(open(path, encoding="utf-8").read())
    assert not problems
    return {a.rule for a in analyze(events)}


def test_buggy_run_trips_every_rule():
    rules = _rules("sample_logs/buggy_run.jsonl")
    assert {"error", "loop", "slow", "empty_result", "token_spike", "secret_leak", "no_final"} <= rules


def test_healthy_run_is_clean():
    assert _rules("sample_logs/healthy_run.jsonl") == set()


def test_bad_lines_are_skipped_not_fatal():
    text = "not json\n" + json.dumps({"step": 1, "event_type": "final"}) + "\n[1,2]\n"
    events, problems = parse_jsonl(text)
    assert len(events) == 1 and len(problems) == 2


def test_aliases_and_dict_inputs():
    events, _ = parse_jsonl(json.dumps({"type": "tool_call", "tool": "x", "args": {"a": 1}, "latency": 12}))
    assert events[0].event_type == "tool_call" and events[0].input == '{"a": 1}' and events[0].latency_ms == 12
