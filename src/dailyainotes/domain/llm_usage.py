"""Records of model calls, shared by the router (which makes them) and the ledger (which
stores them)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CallRecord:
    role: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    ok: bool
    # True when an earlier model in the role's chain failed first.
    fell_back: bool
    error: str = ""


@dataclass(frozen=True)
class Usage:
    requests: int
    tokens: int
