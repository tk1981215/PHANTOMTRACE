"""Local LLM explanations via Ollama. Stdlib only, fails soft if Ollama is not running."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .models import Anomaly, Event

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "gemma3:1b"


def list_models(host: str = DEFAULT_HOST, timeout: float = 1.5) -> list[str] | None:
    """Installed Ollama model names, or None if the server is unreachable."""
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=timeout) as r:
            return [m["name"] for m in json.load(r).get("models", [])]
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError):
        return None


def _clip(text: str | None, n: int = 300) -> str:
    text = (text or "").replace("\n", " ")
    return text if len(text) <= n else text[:n] + "…"


def build_prompt(anomaly: Anomaly, events: list[Event]) -> str:
    near = [e for e in events if abs(e.step - anomaly.step) <= 2]
    lines = [
        f"step {e.step} [{e.event_type}] tool={e.tool} status={e.status} "
        f"in={_clip(e.input)} out={_clip(e.output)}"
        for e in near
    ]
    return (
        "You are PHANTOMTRACE, a calm debugging assistant that reads AI-agent logs.\n"
        f"Detected issue: {anomaly.title} ({anomaly.severity}). {anomaly.detail}\n"
        "Nearby log lines:\n" + "\n".join(lines) + "\n\n"
        "In at most 4 short sentences: what happened, the most likely cause, and one concrete fix."
    )


def explain(
    anomaly: Anomaly,
    events: list[Event],
    model: str = DEFAULT_MODEL,
    host: str = DEFAULT_HOST,
    timeout: float = 180,
) -> str:
    body = json.dumps(
        {
            "model": model,
            "prompt": build_prompt(anomaly, events),
            "stream": False,
            # small context + short answer keeps a 4 GB RAM / CPU-only machine happy
            "options": {"temperature": 0.2, "num_ctx": 2048, "num_predict": 200},
        }
    ).encode()
    req = urllib.request.Request(f"{host}/api/generate", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r).get("response", "").strip() or "(model returned nothing)"
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return f"Model '{model}' is not installed. Run: ollama pull {model}"
        return f"Ollama error: HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError):
        return "Ollama is not reachable. Start it (ollama serve) and pull a model: ollama pull gemma3:1b"
