# backend/app/middleware/metrics.py
# ─────────────────────────────────────────────────────────────────────────────
# In-memory metrics store for the POC.
# Tracks: total requests, total tool calls, cumulative latency, start time.
# Exposed via GET /api/metrics for the frontend metrics panel.
# In production replace with Prometheus counters / OpenTelemetry.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import time
import threading
from dataclasses import dataclass, field


@dataclass
class _Store:
    total_requests: int = 0
    total_latency_ms: int = 0
    total_tool_calls: int = 0
    started_at: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, *, latency_ms: int, tool_calls: int) -> None:
        with self._lock:
            self.total_requests += 1
            self.total_latency_ms += latency_ms
            self.total_tool_calls += tool_calls

    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(self.total_latency_ms / self.total_requests, 1)

    @property
    def uptime_seconds(self) -> float:
        return round(time.time() - self.started_at, 1)


# Singleton metrics store — imported directly by routers
metrics_store = _Store()
