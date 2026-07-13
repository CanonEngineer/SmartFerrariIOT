"""Telemetria e Sync Quality Index — Ferrari Postdoc Lab."""

from __future__ import annotations
import math, statistics, time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class TelemetryEngine:
    window: int = 240
    command_latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=240))
    sync_intervals_ms: deque[float] = field(default_factory=lambda: deque(maxlen=240))
    heartbeats: dict[str, float] = field(default_factory=dict)
    series: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=240))
    total_commands: int = 0
    total_sync_events: int = 0
    desync_events: int = 0
    last_sync_pair_ms: float | None = None
    started_at: float = field(default_factory=time.perf_counter)
    track_points: deque[dict[str, float]] = field(default_factory=lambda: deque(maxlen=120))

    def record_command(self, name: str, latency_ms: float) -> None:
        self.total_commands += 1
        self.command_latencies_ms.append(max(0.0, float(latency_ms)))
        self.series.append({"kind": "command", "name": name, "latency_ms": round(latency_ms, 3), "ts": _utc()})

    def record_heartbeat(self, board: str) -> dict[str, Any]:
        now = time.perf_counter()
        prev = self.heartbeats.get(board)
        self.heartbeats[board] = now
        self.total_sync_events += 1
        if prev is not None:
            self.sync_intervals_ms.append((now - prev) * 1000.0)
        ar, rp = self.heartbeats.get("arduino"), self.heartbeats.get("raspberry")
        pair_ms, synced = None, False
        if ar is not None and rp is not None:
            pair_ms = abs(ar - rp) * 1000.0
            self.last_sync_pair_ms = pair_ms
            synced = pair_ms < 2500.0
            if not synced:
                self.desync_events += 1
        sample = {"ts": _utc(), "board": board, "pair_skew_ms": round(pair_ms, 3) if pair_ms is not None else None, "synced": synced}
        self.series.append({"kind": "heartbeat", **sample})
        return sample

    def record_track(self, lat: float, lon: float) -> None:
        self.track_points.append({"lat": lat, "lon": lon, "t": time.time()})

    def _stats(self, values: deque[float]) -> dict[str, float | None]:
        if not values:
            return {"n": 0, "mean": None, "p50": None, "p95": None, "stdev": None}
        data = sorted(values)
        def pct(p: float) -> float:
            k = (len(data) - 1) * (p / 100.0)
            f, c = math.floor(k), math.ceil(k)
            if f == c:
                return data[int(k)]
            return data[f] * (c - k) + data[c] * (k - f)
        return {
            "n": len(data),
            "mean": round(statistics.fmean(data), 3),
            "p50": round(pct(50), 3),
            "p95": round(pct(95), 3),
            "stdev": round(statistics.pstdev(data), 3) if len(data) > 1 else 0.0,
        }

    def sync_quality_index(self) -> float:
        if self.total_sync_events == 0:
            return 0.0
        skew = self.last_sync_pair_ms
        skew_score = 100.0 if skew is None else max(0.0, 100.0 - min(skew, 5000.0) / 50.0)
        jitter = self._stats(self.sync_intervals_ms)["stdev"] or 0.0
        jitter_score = max(0.0, 100.0 - float(jitter) / 10.0)
        desync_rate = self.desync_events / max(1, self.total_sync_events)
        reliability = max(0.0, 100.0 * (1.0 - min(1.0, desync_rate * 4)))
        return round(0.45 * skew_score + 0.30 * jitter_score + 0.25 * reliability, 2)

    def summary(self) -> dict[str, Any]:
        return {
            "uptime_s": round(time.perf_counter() - self.started_at, 1),
            "protocol_metrics": {
                "total_commands": self.total_commands,
                "total_sync_events": self.total_sync_events,
                "desync_events": self.desync_events,
                "last_pair_skew_ms": round(self.last_sync_pair_ms, 3) if self.last_sync_pair_ms is not None else None,
            },
            "command_latency_ms": self._stats(self.command_latencies_ms),
            "heartbeat_interval_ms": self._stats(self.sync_intervals_ms),
            "sync_quality_index": self.sync_quality_index(),
            "track_points": list(self.track_points)[-40:],
            "series_tail": list(self.series)[-40:],
            "generated_at": _utc(),
        }

telemetry = TelemetryEngine()
