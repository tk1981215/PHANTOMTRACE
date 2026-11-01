# 👻 PHANTOMTRACE

**An offline ghost hunter for AI-agent logs.** Drop in an agent's trace and PHANTOMTRACE finds the hauntings:
loops, silent failures, slow steps, leaked secrets, runs that never finished. Then a small local open-weight
model (Gemma 3 1B via Ollama) explains each one in plain language.

Built for the DEV **Hacktoberfest Open-Source AI Challenge: Week 4 · Ghost in the Machine**.

Everything runs on your machine. No cloud API, no account, no data leaving your laptop.

## Why open-source AI matters here

- **Privacy:** agent logs contain prompts, file paths, tokens and customer data. A local model means the trace never leaves your computer.
- **Works offline:** no internet needed once the model is pulled.
- **Runs on modest hardware:** built and tuned for a 4 GB RAM, CPU-only Windows laptop (1B quantized model, small context window).
- **Free:** no per-token cost, so you can analyze as many runs as you like.
- **Swappable:** pick any model installed in Ollama from the sidebar.

## How it works

```
JSONL log → parser (Pydantic) → rule engine (7 detectors) → SQLite history
                                      │
                                      └→ Streamlit dashboard (Plotly) → "Ask the ghost" → Ollama (Gemma 3 1B)
```

The rules find problems deterministically and instantly. The LLM only does the part that needs language:
explaining the cause and suggesting a fix. That split is what makes a 1B model enough.

| Rule | Severity | Catches |
|---|---|---|
| `error` | high | events with status/type `error` |
| `loop` | high | same tool + same input 3+ times in a row |
| `slow` | medium | latency above max(5 s, mean + 2σ) |
| `empty_result` | medium | tool returned nothing |
| `no_final` | medium | run never produced a `final` event |
| `token_spike` | low | tokens > max(1000, 3× median) |
| `secret_leak` | critical | API keys, AWS keys, bearer tokens, passwords in the trace |

## Setup (Windows + VS Code)

1. Install Python 3.10+ and [Ollama](https://ollama.com/download).
2. Open this folder in VS Code (**File → Open Folder**).
3. In the VS Code terminal (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull gemma3:1b
streamlit run app.py
```

If PowerShell blocks activation, run once:
`Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

Or just double-click **run.bat**, which does the venv + install + launch.

The app opens at http://localhost:8501. It works without Ollama too; only the "Explain" button needs it.

Press **F5** in VS Code to run it under the debugger (select the interpreter in `.venv` first: *Ctrl+Shift+P → Python: Select Interpreter*).

## Log format

One JSON object per line. Only `event_type` is really needed; everything else is optional.

```json
{"step": 7, "timestamp": "2026-10-30T22:00:07Z", "event_type": "tool_call",
 "tool": "read_file", "input": {"path": "a.csv"}, "output": null,
 "latency_ms": 55, "tokens": 120, "status": "ok"}
```

Common aliases are accepted (`type`, `ts`, `latency`, `args`, `result`). Malformed lines are skipped and reported, never fatal.

## Try it

Two sample logs ship in `sample_logs/`:
- `buggy_run.jsonl`: trips every rule (loop, empty file reads, leaked credentials, SQL error, never finishes)
- `healthy_run.jsonl`: a clean run, zero anomalies

The credentials in the buggy sample are fake.

## Tests

```powershell
pytest
```

## Project layout

```
app.py                  Streamlit UI
phantomtrace/
  models.py             Pydantic Event / Anomaly
  parser.py             JSONL parser
  detector.py           7 rule-based detectors
  llm.py                Ollama client (stdlib only, fails soft)
  charts.py             Plotly charts
  store.py              SQLite run history
sample_logs/            demo traces
tests/                  pytest suite
```

## Low-RAM tips (4 GB machines)

- Close the browser tabs and other apps before clicking Explain; the first call loads the model (~1 GB).
- The first explanation can take a minute on CPU. Later ones are faster while the model stays loaded.
- Prompts are capped to the 5 log lines around the anomaly and the context window is 2048 tokens to keep memory low.

## Limitations

- A 1B model gives short, sometimes generic explanations. The rule engine is the source of truth.
- Rules are heuristics with fixed thresholds; tune them in `phantomtrace/detector.py`.
- Only JSONL logs are supported for now.

## License

MIT
