from phantomtrace import store
from phantomtrace.detector import analyze
from phantomtrace.parser import parse_jsonl


def test_roundtrip(tmp_path):
    db = str(tmp_path / "t.db")
    events, _ = parse_jsonl(open("sample_logs/buggy_run.jsonl", encoding="utf-8").read())
    anomalies = analyze(events)
    run_id = store.save_run("buggy", events, anomalies, db)
    name, ev2, an2 = store.load_run(run_id, db)
    assert name == "buggy" and len(ev2) == len(events) and len(an2) == len(anomalies)
    assert store.list_runs(db)[0][0] == run_id
