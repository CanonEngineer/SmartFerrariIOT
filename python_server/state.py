"""Estado vivo da Ferrari + placas Arduino/Raspberry."""

from __future__ import annotations
import asyncio, time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from protocol import PROTOCOL_VERSION
from telemetry import telemetry
from statemachine import digital_twin
from security import audit_chain, sign_payload
from energy import energy_model
from hil import hil

BroadcastFn = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()

class FerrariState:
    def __init__(self) -> None:
        self.sensors = {
            "rpm": 800.0, "speed_kmh": 0.0, "engine_temp": 78.0,
            "battery": 92.0, "fuel": 68.0, "lat": -23.5505, "lon": -46.6333, "power_w": 0.0,
        }
        self.actuators = {
            "door": {"driver": False, "passenger": False}, "roof": False, "engine": False,
            "sound": False, "headlight": False, "tracking": False, "alarm": True,
            "spoiler": False, "climate": False, "horn": False, "sport_mode": False,
            "lock": True, "brake_light": False, "ignition": False,
        }
        self.boards = {
            "arduino": {"id": "arduino-ferrari", "name": "Arduino Ferrari", "online": True, "sync": True,
                        "last_heartbeat": _utc(), "role": "atuação veicular + sensores", "layer": "L1"},
            "raspberry": {"id": "raspberry-hub", "name": "Raspberry Pi Hub", "online": True, "sync": True,
                          "last_heartbeat": _utc(), "role": "coordenação edge + tracking", "layer": "L3"},
        }
        self.sync_pulse = 0
        self.state_version = 0
        self.last_event = "Ferrari Lab iniciado"
        self.energy = energy_model.compute(self.actuators, self.sensors, 0).to_dict()
        self._listeners: list[BroadcastFn] = []
        self._lock = asyncio.Lock()
        self._last_energy_ts = time.perf_counter()
        digital_twin.bind(self.actuators, self.sensors)

    def snapshot(self) -> dict[str, Any]:
        digital_twin.bind(self.actuators, self.sensors)
        return {
            "protocol_version": PROTOCOL_VERSION,
            "state_version": self.state_version,
            "sensors": deepcopy(self.sensors),
            "actuators": deepcopy(self.actuators),
            "boards": deepcopy(self.boards),
            "sync_pulse": self.sync_pulse,
            "last_event": self.last_event,
            "sync_quality_index": telemetry.sync_quality_index(),
            "pair_skew_ms": telemetry.last_sync_pair_ms,
            "twin": digital_twin.ctx.snapshot(),
            "energy": self.energy,
            "hil": hil.snapshot(),
            "audit_tip": audit_chain.tip(),
            "timestamp": _utc(),
        }

    def add_listener(self, fn: BroadcastFn) -> None:
        self._listeners.append(fn)

    def remove_listener(self, fn: BroadcastFn) -> None:
        if fn in self._listeners:
            self._listeners.remove(fn)

    async def broadcast(self, event: str | None = None) -> None:
        if event:
            self.last_event = event
        payload = {"type": "state", "data": self.snapshot()}
        dead = []
        for listener in list(self._listeners):
            try:
                await listener(payload)
            except Exception:
                dead.append(listener)
        for listener in dead:
            self.remove_listener(listener)

    def _bump(self, action: str) -> None:
        now = _utc()
        self.boards["arduino"]["last_heartbeat"] = now
        self.boards["raspberry"]["last_heartbeat"] = now
        self.boards["arduino"]["sync"] = True
        self.boards["raspberry"]["sync"] = True
        self.sync_pulse = (self.sync_pulse + 1) % 1000
        self.state_version += 1
        self.last_event = action
        audit_chain.append(action, sign_payload({"action": action, "v": self.state_version}))

    def _tick_energy(self) -> None:
        now = time.perf_counter()
        dt = now - self._last_energy_ts
        self._last_energy_ts = now
        snap = energy_model.compute(self.actuators, self.sensors, dt)
        self.sensors["battery"] = snap.battery_pct
        self.sensors["fuel"] = snap.fuel_pct
        self.sensors["power_w"] = snap.power_w
        self.energy = snap.to_dict()

    async def _timed(self, name: str, params: dict, mutate) -> dict[str, Any]:
        async def _run():
            t0 = time.perf_counter()
            async with self._lock:
                digital_twin.bind(self.actuators, self.sensors)
                digital_twin.guard(name, params)
                mutate()
                self._tick_energy()
                digital_twin.bind(self.actuators, self.sensors)
                telemetry.record_command(name, (time.perf_counter() - t0) * 1000.0)
                await self.broadcast(self.last_event)
                return self.snapshot()

        delivered, result = await hil.apply(name, _run)
        if not delivered:
            raise ValueError(f"HIL drop: comando '{name}' perdido (loss_rate={hil.config.loss_rate})")
        return result

    async def set_door(self, which: str, open_: bool) -> dict[str, Any]:
        def m():
            if which not in self.actuators["door"]:
                raise ValueError(f"Porta inválida: {which}")
            if self.actuators["lock"] and open_:
                self.actuators["lock"] = False
            self.actuators["door"][which] = open_
            self._bump(f"DOOR {which}={'OPEN' if open_ else 'CLOSE'}")
        return await self._timed("door", {"open": open_, "door_id": which}, m)

    async def set_roof(self, open_: bool) -> dict[str, Any]:
        def m():
            self.actuators["roof"] = open_
            self._bump(f"ROOF={'OPEN' if open_ else 'CLOSE'}")
        return await self._timed("roof", {"open": open_}, m)

    async def set_engine(self, on: bool) -> dict[str, Any]:
        def m():
            self.actuators["engine"] = on
            self.actuators["ignition"] = on
            if on:
                self.actuators["alarm"] = False
                self.sensors["rpm"] = 1200.0
            else:
                self.sensors["rpm"] = 0.0
                self.sensors["speed_kmh"] = 0.0
                self.actuators["sport_mode"] = False
            self._bump(f"ENGINE={'ON' if on else 'OFF'}")
        return await self._timed("engine", {"on": on}, m)

    async def set_sound(self, on: bool) -> dict[str, Any]:
        def m():
            self.actuators["sound"] = on
            self._bump(f"SOUND={'ON' if on else 'OFF'}")
        return await self._timed("sound", {"on": on}, m)

    async def set_headlight(self, on: bool) -> dict[str, Any]:
        def m():
            self.actuators["headlight"] = on
            self._bump(f"HEADLIGHT={'ON' if on else 'OFF'}")
        return await self._timed("headlight", {"on": on}, m)

    async def set_tracking(self, on: bool) -> dict[str, Any]:
        def m():
            self.actuators["tracking"] = on
            self._bump(f"TRACK={'ON' if on else 'OFF'}")
        return await self._timed("track", {"on": on}, m)

    async def set_alarm(self, armed: bool) -> dict[str, Any]:
        def m():
            self.actuators["alarm"] = armed
            if armed:
                self.actuators["engine"] = False
                self.actuators["ignition"] = False
                self.actuators["lock"] = True
                self.actuators["door"]["driver"] = False
                self.actuators["door"]["passenger"] = False
            self._bump(f"ALARM={'ARMED' if armed else 'DISARMED'}")
        return await self._timed("alarm", {"on": armed}, m)

    async def set_spoiler(self, deployed: bool) -> dict[str, Any]:
        def m():
            self.actuators["spoiler"] = deployed
            self._bump(f"SPOILER={'OUT' if deployed else 'IN'}")
        return await self._timed("spoiler", {"on": deployed}, m)

    async def set_climate(self, on: bool) -> dict[str, Any]:
        def m():
            self.actuators["climate"] = on
            self._bump(f"CLIMATE={'ON' if on else 'OFF'}")
        return await self._timed("climate", {"on": on}, m)

    async def set_horn(self, on: bool) -> dict[str, Any]:
        def m():
            self.actuators["horn"] = on
            self._bump(f"HORN={'ON' if on else 'OFF'}")
        snap = await self._timed("horn", {"on": on}, m)
        if on:
            async def _auto_off() -> None:
                await asyncio.sleep(0.45)
                def off():
                    if self.actuators.get("horn"):
                        self.actuators["horn"] = False
                        self._bump("HORN=OFF")
                async with self._lock:
                    off()
                    await self.broadcast(self.last_event)
            asyncio.create_task(_auto_off())
        return snap

    async def set_sport_mode(self, on: bool) -> dict[str, Any]:
        def m():
            self.actuators["sport_mode"] = on
            if on:
                self.actuators["spoiler"] = True
            self._bump(f"SPORT={'ON' if on else 'OFF'}")
        return await self._timed("sport", {"on": on}, m)

    async def set_lock(self, locked: bool) -> dict[str, Any]:
        def m():
            self.actuators["lock"] = locked
            if locked:
                self.actuators["door"]["driver"] = False
                self.actuators["door"]["passenger"] = False
            self._bump(f"LOCK={'ON' if locked else 'OFF'}")
        return await self._timed("lock", {"on": locked}, m)

    async def update_sensors(self, **kwargs: Any) -> dict[str, Any]:
        async with self._lock:
            for k, v in kwargs.items():
                if k in self.sensors:
                    self.sensors[k] = v
            self._tick_energy()
            if self.actuators["tracking"]:
                telemetry.record_track(self.sensors["lat"], self.sensors["lon"])
            self.state_version += 1
            await self.broadcast("Telemetria atualizada")
            return self.snapshot()

    async def heartbeat(self, board: str) -> dict[str, Any]:
        async with self._lock:
            if board not in self.boards:
                raise ValueError(f"Placa inválida: {board}")
            self.boards[board]["online"] = True
            self.boards[board]["last_heartbeat"] = _utc()
            sample = telemetry.record_heartbeat(board)
            synced = bool(sample.get("synced"))
            self.boards["arduino"]["sync"] = synced
            self.boards["raspberry"]["sync"] = synced
            self.sync_pulse = (self.sync_pulse + 1) % 1000
            self.state_version += 1
            await self.broadcast(f"Heartbeat {board}")
            return self.snapshot()

ferrari_state = FerrariState()
