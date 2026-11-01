from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .models import Anomaly

SEV_COLOR = {"low": "#7FDBFF", "medium": "#FFDC00", "high": "#FF851B", "critical": "#FF4136"}
TYPE_COLOR = {
    "thought": "#6C7A89",
    "tool_call": "#4DA3FF",
    "tool_result": "#7CFC9A",
    "error": "#FF4136",
    "final": "#C792EA",
}


def events_frame(events) -> pd.DataFrame:
    return pd.DataFrame([e.model_dump() for e in events])


def latency_timeline(df: pd.DataFrame, anomalies: list[Anomaly]) -> go.Figure:
    fig = go.Figure()
    d = df.fillna({"latency_ms": 0})
    for etype, g in d.groupby("event_type"):
        fig.add_bar(x=g["step"], y=g["latency_ms"], name=etype, marker_color=TYPE_COLOR.get(etype, "#999"))
    ymax = max(float(d["latency_ms"].max()), 1.0)
    for sev in ("low", "medium", "high", "critical"):
        pts = [a for a in anomalies if a.severity == sev]
        if pts:
            fig.add_scatter(
                x=[a.step for a in pts],
                y=[ymax * 1.08] * len(pts),
                mode="markers",
                hovertext=[a.title for a in pts],
                marker=dict(size=13, color=SEV_COLOR[sev], symbol="diamond"),
                name=f"{sev} anomaly",
            )
    fig.update_layout(
        template="plotly_dark",
        title="Latency per step (diamonds mark anomalies)",
        xaxis_title="step",
        yaxis_title="latency (ms)",
        barmode="stack",
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def token_chart(df: pd.DataFrame) -> go.Figure:
    d = df.dropna(subset=["tokens"])
    fig = go.Figure(go.Scatter(x=d["step"], y=d["tokens"], mode="lines+markers", line_color="#7CFC9A"))
    fig.update_layout(
        template="plotly_dark",
        title="Tokens per step",
        xaxis_title="step",
        yaxis_title="tokens",
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig
