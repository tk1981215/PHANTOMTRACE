from __future__ import annotations

import json
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

Severity = Literal["low", "medium", "high", "critical"]
SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class Event(BaseModel):
    """One line of an agent log."""

    step: int
    timestamp: Optional[datetime] = None
    event_type: str = "unknown"  # thought | tool_call | tool_result | error | final ...
    tool: Optional[str] = None
    input: Optional[str] = None
    output: Optional[str] = None
    latency_ms: Optional[float] = None
    tokens: Optional[int] = None
    status: str = "ok"

    @field_validator("input", "output", mode="before")
    @classmethod
    def _stringify(cls, v):
        if v is None or isinstance(v, str):
            return v
        return json.dumps(v, ensure_ascii=False, sort_keys=True)


class Anomaly(BaseModel):
    """Something suspicious the rule engine found."""

    step: int
    rule: str
    severity: Severity
    title: str
    detail: str
