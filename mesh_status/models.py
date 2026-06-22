from dataclasses import dataclass, field


@dataclass
class NodeRegistration:
    node_ip: str
    hostname: str | None = None


@dataclass
class CheckResult:
    node_ip: str
    target_ip: str
    ping_ok: bool
    ping_latency_ms: float | None = None
    http_ok: bool = False
    http_latency_ms: float | None = None
    http_status: int | None = None
    timestamp: float = 0.0


@dataclass
class SubmitPayload:
    node_ip: str
    checks: list[CheckResult] = field(default_factory=list)
    timestamp: float = 0.0


@dataclass
class NodeInfo:
    node_ip: str
    hostname: str | None = None
    last_seen: float = 0.0
    listen_port: int = 58080
    node_url: str | None = None
