"""Experimentos reproduzíveis — pós-doutorado Ferrari IoT."""

from __future__ import annotations
import asyncio, csv, io, json, time, uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from sqlalchemy.orm import Session
from database import log_action
from state import ferrari_state
from telemetry import telemetry

EXPORT_DIR = Path(__file__).resolve().parent.parent / "experiments" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class ExperimentResult:
    experiment_id: str
    name: str
    hypothesis: str
    started_at: str
    finished_at: str
    parameters: dict[str, Any]
    samples: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class ExperimentRunner:
    CATALOG = {
        "sync_latency": {
            "title": "Latência de sincronização Arduino↔Raspberry",
            "hypothesis": "Skew entre heartbeats permanece < 100 ms em regime estável.",
            "default_params": {"cycles": 16, "delay_ms": 180},
        },
        "actuator_chain": {
            "title": "Cadeia de atuação veicular",
            "hypothesis": "Mediana de latência de porta/teto/farol < 50 ms no caminho API→estado.",
            "default_params": {"cycles": 10},
        },
        "tracking_stability": {
            "title": "Estabilidade do rastreamento GPS",
            "hypothesis": "Com tracking ON, pontos GPS formam trajetória contínua sem saltos > 0.01°.",
            "default_params": {"seconds": 6},
        },
        "fault_injection": {
            "title": "Injeção de atraso de sync",
            "hypothesis": "SQI cai sob atraso artificial e recupera após restabelecimento.",
            "default_params": {"delay_ms": 900, "recovery_cycles": 8},
        },
    }

    def __init__(self) -> None:
        self.history: list[ExperimentResult] = []

    async def run(self, name: str, db: Session, params: dict | None = None) -> ExperimentResult:
        if name not in self.CATALOG:
            raise ValueError(f"Inválido. Use: {', '.join(self.CATALOG)}")
        meta = self.CATALOG[name]
        parameters = {**meta["default_params"], **(params or {})}
        exp_id = str(uuid.uuid4())[:8]
        started, t0 = _utc(), time.perf_counter()
        if name == "sync_latency":
            samples = await self._sync(parameters)
        elif name == "actuator_chain":
            samples = await self._actuators(parameters)
        elif name == "tracking_stability":
            samples = await self._tracking(parameters)
        else:
            samples = await self._fault(parameters)
        result = ExperimentResult(
            experiment_id=exp_id, name=name, hypothesis=meta["hypothesis"],
            started_at=started, finished_at=_utc(), parameters=parameters, samples=samples,
            metrics={**telemetry.summary(), "wall_time_s": round(time.perf_counter() - t0, 3), "sample_count": len(samples)},
        )
        self.history.append(result)
        self._persist(result)
        log_action(db, "research-lab", "experiment", f"{name}:{exp_id}")
        return result

    async def _sync(self, p: dict) -> list[dict]:
        samples = []
        for i in range(int(p["cycles"])):
            t0 = time.perf_counter()
            await ferrari_state.heartbeat("arduino")
            await asyncio.sleep(int(p["delay_ms"]) / 1000)
            await ferrari_state.heartbeat("raspberry")
            dt = (time.perf_counter() - t0) * 1000
            telemetry.record_command("sync_cycle", dt)
            samples.append({"cycle": i + 1, "cycle_ms": round(dt, 3), "sqi": telemetry.sync_quality_index()})
        return samples

    async def _actuators(self, p: dict) -> list[dict]:
        samples = []
        for i in range(int(p["cycles"])):
            for name, coro in (
                ("door", ferrari_state.set_door("driver", i % 2 == 0)),
                ("roof", ferrari_state.set_roof(i % 2 == 0)),
                ("headlight", ferrari_state.set_headlight(i % 2 == 0)),
            ):
                t0 = time.perf_counter()
                await coro
                samples.append({"cycle": i + 1, "action": name, "latency_ms": round((time.perf_counter() - t0) * 1000, 3)})
        return samples

    async def _tracking(self, p: dict) -> list[dict]:
        await ferrari_state.set_tracking(True)
        await asyncio.sleep(float(p["seconds"]))
        pts = list(telemetry.track_points)
        jumps = []
        for a, b in zip(pts, pts[1:]):
            jumps.append(abs(a["lat"] - b["lat"]) + abs(a["lon"] - b["lon"]))
        return [{"points": len(pts), "max_jump": max(jumps) if jumps else 0, "sqi": telemetry.sync_quality_index()}]

    async def _fault(self, p: dict) -> list[dict]:
        samples = [{"phase": "pre", "sqi": telemetry.sync_quality_index()}]
        await ferrari_state.heartbeat("arduino")
        await asyncio.sleep(int(p["delay_ms"]) / 1000)
        await ferrari_state.heartbeat("raspberry")
        samples.append({"phase": "fault", "sqi": telemetry.sync_quality_index()})
        for i in range(int(p["recovery_cycles"])):
            await ferrari_state.heartbeat("arduino")
            await asyncio.sleep(0.05)
            await ferrari_state.heartbeat("raspberry")
            samples.append({"phase": "recovery", "cycle": i + 1, "sqi": telemetry.sync_quality_index()})
        return samples

    def _persist(self, result: ExperimentResult) -> None:
        base = EXPORT_DIR / f"{result.name}_{result.experiment_id}"
        base.with_suffix(".json").write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        if result.samples:
            keys = []
            for row in result.samples:
                for k in row:
                    if k not in keys:
                        keys.append(k)
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=keys)
            w.writeheader()
            w.writerows(result.samples)
            base.with_suffix(".csv").write_text(buf.getvalue(), encoding="utf-8")

    def export_bundle(self, experiment_id: str) -> dict[str, Any]:
        for item in reversed(self.history):
            if item.experiment_id == experiment_id:
                base = EXPORT_DIR / f"{item.name}_{item.experiment_id}"
                return {"experiment": item.to_dict(), "json_path": str(base.with_suffix(".json")), "csv_path": str(base.with_suffix(".csv"))}
        raise ValueError("Experimento não encontrado")

experiment_runner = ExperimentRunner()
