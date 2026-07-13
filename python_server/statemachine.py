"""
Gêmeo digital formal — máquina de estados / statechart com invariantes.

Modos: SECURE → IDLE → READY → RUNNING → SPORT
Eventos inválidos levantam InvariantViolation (rejeição segura).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Mode(str, Enum):
    SECURE = "SECURE"
    IDLE = "IDLE"
    READY = "READY"
    RUNNING = "RUNNING"
    SPORT = "SPORT"


class InvariantViolation(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass
class TwinContext:
    actuators: dict[str, Any]
    sensors: dict[str, Any]
    mode: Mode = Mode.SECURE
    last_rejected: list[dict[str, str]] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "invariants": INVARIANT_CATALOG,
            "transitions": TRANSITION_TABLE,
            "last_rejected": self.last_rejected[-10:],
        }


INVARIANT_CATALOG = [
    {"id": "INV-01", "rule": "Não abrir porta se sport_mode AND speed_kmh > 0"},
    {"id": "INV-02", "rule": "Não ligar motor se alarm armado"},
    {"id": "INV-03", "rule": "Não entrar em SPORT sem engine ON"},
    {"id": "INV-04", "rule": "Não abrir teto se speed_kmh > 40"},
    {"id": "INV-05", "rule": "Travar implica fechar portas"},
    {"id": "INV-06", "rule": "SECURE exige engine OFF e lock ON"},
]

TRANSITION_TABLE = {
    "SECURE": ["IDLE"],
    "IDLE": ["SECURE", "READY"],
    "READY": ["IDLE", "RUNNING", "SECURE"],
    "RUNNING": ["READY", "SPORT", "IDLE"],
    "SPORT": ["RUNNING", "READY"],
}


class DigitalTwin:
    def __init__(self) -> None:
        self.ctx = TwinContext(actuators={}, sensors={})

    def bind(self, actuators: dict, sensors: dict) -> None:
        self.ctx.actuators = actuators
        self.ctx.sensors = sensors
        self._recompute_mode()

    def _recompute_mode(self) -> None:
        a, s = self.ctx.actuators, self.ctx.sensors
        if a.get("alarm") and a.get("lock") and not a.get("engine"):
            self.ctx.mode = Mode.SECURE
        elif a.get("sport_mode") and a.get("engine"):
            self.ctx.mode = Mode.SPORT
        elif a.get("engine"):
            self.ctx.mode = Mode.RUNNING
        elif not a.get("lock") and not a.get("alarm"):
            self.ctx.mode = Mode.READY if a.get("ignition") or True else Mode.IDLE
            if not a.get("engine") and not a.get("alarm"):
                self.ctx.mode = Mode.READY if not a.get("lock") else Mode.IDLE
        else:
            self.ctx.mode = Mode.IDLE

    def guard(self, action: str, params: dict[str, Any] | None = None) -> None:
        """Valida invariantes antes da mutação. params descreve a intenção."""
        params = params or {}
        a, s = self.ctx.actuators, self.ctx.sensors
        speed = float(s.get("speed_kmh") or 0)

        try:
            if action == "door" and params.get("open"):
                if a.get("sport_mode") and speed > 0:
                    raise InvariantViolation("INV-01", "Porta bloqueada: Sport + velocidade > 0")
                if a.get("lock"):
                    # auto-unlock allowed only if not SECURE with alarm? allow unlock path separately
                    pass
            if action == "engine" and params.get("on") and a.get("alarm"):
                raise InvariantViolation("INV-02", "Motor bloqueado: alarme armado")
            if action == "sport" and params.get("on") and not a.get("engine"):
                raise InvariantViolation("INV-03", "Sport requer motor ligado")
            if action == "roof" and params.get("open") and speed > 40:
                raise InvariantViolation("INV-04", "Teto bloqueado: velocidade > 40 km/h")
            if action == "lock" and params.get("on"):
                # will force doors closed in mutate
                pass
            if action == "alarm" and params.get("on") and a.get("engine"):
                raise InvariantViolation("INV-06", "Não armar alarme com motor ligado")
        except InvariantViolation as exc:
            self.ctx.last_rejected.append({"code": exc.code, "message": str(exc), "action": action})
            raise

        self._recompute_mode()


digital_twin = DigitalTwin()
