from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NodeRegistration:
    node_ip: str
    hostname: Optional[str] = None


@dataclass
class CheckResult:
    node_ip: str
    target_ip: str
    ping_ok: bool
    ping_latency_ms: Optional[float] = None
    http_ok: bool = False
    http_latency_ms: Optional[float] = None
    http_status: Optional[int] = None
    timestamp: float = 0.0


@dataclass
class SubmitPayload:
    node_ip: str
    checks: list[CheckResult] = field(default_factory=list)
    timestamp: float = 0.0


@dataclass
class NodeInfo:
    node_ip: str
    hostname: Optional[str] = None
    last_seen: float = 0.0
