"""
Co-simulação HIL: atraso e perda de pacote configuráveis + métricas QoS.
"""

from __future__ import annotations
import asyncio
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass
class HILConfig:
    delay_ms: float = 0.0
    loss_rate: float = 0.0  # 0..1
    enabled: bool = False


@dataclass
class HILEngine:
    config: HILConfig = field(default_factory=HILConfig)
    sent: int = 0
    delivered: int = 0
    dropped: int = 0
    latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=200))
    events: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=100))

    def configure(self, delay_ms: float | None = None, loss_rate: float | None = None, enabled: bool | None = None) -> dict:
        if delay_ms is not None:
            self.config.delay_ms = max(0.0, float(delay_ms))
        if loss_rate is not None:
            self.config.loss_rate = min(1.0, max(0.0, float(loss_rate)))
        if enabled is not None:
            self.config.enabled = bool(enabled)
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        delivered = max(1, self.delivered)
        mean_lat = sum(self.latencies_ms) / len(self.latencies_ms) if self.latencies_ms else None
        return {
            "enabled": self.config.enabled,
            "delay_ms": self.config.delay_ms,
            "loss_rate": self.config.loss_rate,
            "qos": {
                "sent": self.sent,
                "delivered": self.delivered,
                "dropped": self.dropped,
                "delivery_ratio": round(self.delivered / max(1, self.sent), 4),
                "loss_observed": round(self.dropped / max(1, self.sent), 4),
                "mean_latency_ms": round(mean_lat, 3) if mean_lat is not None else None,
                "consistency": "eventual" if self.config.enabled and (self.config.delay_ms > 0 or self.config.loss_rate > 0) else "strong-lab",
            },
            "recent": list(self.events)[-20:],
        }

    async def apply(self, name: str, coro_factory: Callable[[], Awaitable[Any]]) -> tuple[bool, Any]:
        """
        Executa comando sob HIL. Retorna (delivered, result|None).
        coro_factory deve criar a coroutine no momento da entrega (após delay).
        """
        self.sent += 1
        t0 = time.perf_counter()
        if self.config.enabled and random.random() < self.config.loss_rate:
            self.dropped += 1
            self.events.append({"name": name, "status": "DROPPED", "t": time.time()})
            return False, None
        if self.config.enabled and self.config.delay_ms > 0:
            await asyncio.sleep(self.config.delay_ms / 1000.0)
        result = await coro_factory()
        dt = (time.perf_counter() - t0) * 1000.0
        self.delivered += 1
        self.latencies_ms.append(dt)
        self.events.append({"name": name, "status": "DELIVERED", "latency_ms": round(dt, 3), "t": time.time()})
        return True, result


hil = HILEngine()
