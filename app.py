"""PHANTOMTRACE - offline ghost hunter for AI-agent logs. Run: streamlit run app.py"""
from pathlib import Path

import pandas as pd
import streamlit as st

from phantomtrace import llm, store
from phantomtrace.charts import events_frame, latency_timeline, token_chart
from phantomtrace.detector import analyze
from phantomtrace.parser import parse_jsonl

st.set_page_config(page_title="PHANTOMTRACE", page_icon="👻", layout="wide")
SAMPLES = {p.name: p for p in sorted(Path("sample_logs").glob("*.jsonl"))}
SEV_ICON = {"low": "🔵", "medium": "🟡", "high": "🟠", "critical": "🔴"}

st.title("👻 PHANTOMTRACE")
st.caption("An offline ghost hunter for AI-agent logs. Everything runs on this machine. Nothing is uploaded.")

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Séance setup")
    source = st.radio("Log source", ["Bundled sample", "Upload a log", "Past runs"])
    text, run_name = None, None

    if source == "Bundled sample" and SAMPLES:
        run_name = st.selectbox("Sample", list(SAMPLES))
        text = SAMPLES[run_name].read_text(encoding="utf-8")
    elif source == "Upload a log":
        up = st.file_uploader("JSONL agent log", type=["jsonl", "log", "txt", "json"])
        if up:
            run_name, text = up.name, up.getvalue().decode("utf-8", errors="replace")
    else:
        history = store.list_runs()
        if history:
            labels = {f"#{i} · {n} · {c}": i for i, n, c in history}
            run_id = labels[st.selectbox("Saved investigation", list(labels))]
        else:
            run_id = None
            st.info("No saved runs yet.")

    st.divider()
    installed = llm.list_models()
    model = llm.DEFAULT_MODEL
    if installed is None:
        st.warning("Ollama is offline. Detection still works; AI explanations are disabled.")
    else:
        st.success("Ollama is online")
        model = st.selectbox("Local model", installed or [llm.DEFAULT_MODEL])
        if not installed:
            st.caption(f"No models yet. Run: ollama pull {llm.DEFAULT_MODEL}")
    save_history = st.checkbox("Save run to local SQLite", value=True)

# ---------------------------------------------------------------- load / analyze
events, anomalies, problems = [], [], []
if source == "Past runs":
    if history:
        run_name, events, anomalies = store.load_run(run_id)
elif text:
    events, problems = parse_jsonl(text)
    anomalies = analyze(events)
    key = f"{run_name}:{len(text)}"
    if save_history and events and st.session_state.get("saved_key") != key:
        store.save_run(run_name, events, anomalies)
        st.session_state["saved_key"] = key

if not events:
    st.info("Pick a bundled sample, or upload a JSONL agent log from the sidebar to begin.")
    st.stop()

for p in problems[:5]:
    st.warning(f"Skipped {p}")

# ---------------------------------------------------------------- metrics
df = events_frame(events)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Events", len(events))
c2.metric("Anomalies", len(anomalies))
c3.metric("Critical / High", sum(a.severity in ("critical", "high") for a in anomalies))
c4.metric("Total latency", f"{df['latency_ms'].fillna(0).sum() / 1000:.1f} s")

tab_hunt, tab_trace, tab_raw = st.tabs(["🔦 Hauntings", "📈 Timeline", "🗂 Raw trace"])

with tab_hunt:
    if not anomalies:
        st.success("No ghosts found. This run looks clean.")
    else:
        table = pd.DataFrame(
            [{"": SEV_ICON[a.severity], "step": a.step, "severity": a.severity, "issue": a.title, "detail": a.detail} for a in anomalies]
        )
        st.dataframe(table, width="stretch", hide_index=True)

        st.subheader("Ask the ghost")
        options = {f"{SEV_ICON[a.severity]} step {a.step} · {a.title}": i for i, a in enumerate(anomalies)}
        idx = options[st.selectbox("Pick a haunting to investigate", list(options))]
        cache = st.session_state.setdefault("explanations", {})
        ckey = (run_name, idx, model)
        if st.button("Explain with local model", disabled=installed is None):
            with st.spinner(f"{model} is reading the trace (CPU only, this can take a minute)..."):
                cache[ckey] = llm.explain(anomalies[idx], events, model=model)
        if ckey in cache:
            st.markdown(f"> {cache[ckey]}")

with tab_trace:
    st.plotly_chart(latency_timeline(df, anomalies), width="stretch")
    if df["tokens"].notna().any():
        st.plotly_chart(token_chart(df), width="stretch")

with tab_raw:
    st.dataframe(df, width="stretch", hide_index=True)
