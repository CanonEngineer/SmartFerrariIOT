"""Simulador de telemetria e cenários Ferrari."""

from __future__ import annotations
import asyncio, math, random
from datetime import datetime
from sqlalchemy.orm import Session
from config import settings
from database import log_action
from models import TelemetrySample
from state import ferrari_state

class FerrariSimulator:
    def __init__(self) -> None:
        self._task = None
        self._running = False
        self._t0 = datetime.utcnow().timestamp()

    async def start(self, db_factory) -> None:
        if not settings.simulation_mode or self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(db_factory))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self, db_factory) -> None:
        angle = 0.0
        while self._running:
            elapsed = datetime.utcnow().timestamp() - self._t0
            a = ferrari_state.actuators
            if a["engine"]:
                base = 3500 if a["sport_mode"] else 1800
                rpm = base + 400 * math.sin(elapsed / 2) + random.uniform(-50, 50)
                speed = (45 if a["sport_mode"] else 18) + 8 * math.sin(elapsed / 4)
                temp = 88 + 6 * math.sin(elapsed / 20) + random.uniform(-0.5, 0.5)
            else:
                rpm, speed, temp = 0.0, 0.0, 72 + random.uniform(-0.3, 0.3)
            if a["tracking"]:
                angle += 0.08
                lat = -23.5505 + 0.004 * math.sin(angle)
                lon = -46.6333 + 0.004 * math.cos(angle)
            else:
                lat, lon = ferrari_state.sensors["lat"], ferrari_state.sensors["lon"]
            fuel = max(5, ferrari_state.sensors["fuel"] - (0.02 if a["engine"] else 0))
            battery = max(40, 92 - (0.01 if a["headlight"] or a["sound"] else 0))
            await ferrari_state.update_sensors(
                rpm=round(rpm, 0), speed_kmh=round(max(0, speed), 1),
                engine_temp=round(temp, 1), lat=round(lat, 6), lon=round(lon, 6),
                fuel=round(fuel, 1), battery=round(battery, 1),
            )
            db = db_factory()
            try:
                db.add(TelemetrySample(rpm=rpm, speed_kmh=speed, engine_temp=temp, lat=lat, lon=lon))
                db.commit()
            finally:
                db.close()
            await ferrari_state.heartbeat("arduino")
            await asyncio.sleep(0.35)
            await ferrari_state.heartbeat("raspberry")
            await asyncio.sleep(settings.sensor_interval_seconds)

    async def run_scenario(self, name: str, db: Session) -> dict:
        name = name.lower().strip()
        if name == "startup":
            await ferrari_state.set_alarm(False)
            await ferrari_state.set_lock(False)
            await ferrari_state.set_engine(True)
            await ferrari_state.set_headlight(True)
            await ferrari_state.set_sound(True)
        elif name == "track_day":
            await ferrari_state.set_alarm(False)
            await ferrari_state.set_engine(True)
            await ferrari_state.set_sport_mode(True)
            await ferrari_state.set_spoiler(True)
            await ferrari_state.set_tracking(True)
            await ferrari_state.set_roof(True)
        elif name == "valet":
            await ferrari_state.set_engine(False)
            await ferrari_state.set_door("driver", True)
            await ferrari_state.set_climate(True)
            await ferrari_state.set_sound(True)
        elif name == "secure":
            await ferrari_state.set_engine(False)
            await ferrari_state.set_roof(False)
            await ferrari_state.set_door("driver", False)
            await ferrari_state.set_door("passenger", False)
            await ferrari_state.set_lock(True)
            await ferrari_state.set_alarm(True)
            await ferrari_state.set_headlight(False)
            await ferrari_state.set_sound(False)
            await ferrari_state.set_tracking(False)
        elif name == "sync_test":
            for _ in range(6):
                await ferrari_state.set_headlight(True)
                await ferrari_state.heartbeat("arduino")
                await asyncio.sleep(0.25)
                await ferrari_state.set_headlight(False)
                await ferrari_state.heartbeat("raspberry")
                await asyncio.sleep(0.25)
        else:
            raise ValueError("Cenários: startup, track_day, valet, secure, sync_test")
        log_action(db, "system", "scenario", name)
        return {"ok": True, "scenario": name, "state": ferrari_state.snapshot()}

simulator = FerrariSimulator()
