"""
Modelo energético veicular (documentado).

Potências nominais (W) — ordem de grandeza para bancada:
  P_motor(rpm) ≈ P0 + k_rpm * rpm
  P_farol, P_som, P_ac, P_track constantes

ΔE_bat (Wh) ≈ -Σ P_i * Δt_h
Δfuel (%) ≈ -α * P_motor * Δt_h   (proxy térmico)

Bateria: capacidade nominal C_bat = 12 V · 60 Ah ≈ 720 Wh (escala lab)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

# Constantes documentadas (lab-scale)
P_HEADLIGHT_W = 120.0
P_SOUND_W = 80.0
P_CLIMATE_W = 150.0
P_TRACK_W = 15.0
P_SPOILER_W = 25.0
P0_ENGINE_W = 200.0
K_RPM = 0.08  # W/rpm proxy
BATTERY_CAPACITY_WH = 720.0
FUEL_ALPHA = 0.00012  # % fuel per W·h


@dataclass
class EnergySnapshot:
    power_w: float
    battery_pct: float
    fuel_pct: float
    components: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "power_w": round(self.power_w, 2),
            "battery_pct": round(self.battery_pct, 2),
            "fuel_pct": round(self.fuel_pct, 2),
            "components_w": {k: round(v, 2) for k, v in self.components.items()},
            "equations": {
                "P_total": "P_motor(rpm)+P_hl+P_sound+P_ac+P_track+P_spoiler",
                "P_motor": "P0 + k_rpm * rpm",
                "dE_bat": "-P_total * dt_hours",
                "dfuel": "-alpha * P_motor * dt_hours",
            },
        }


class EnergyModel:
    def compute(self, actuators: dict, sensors: dict, dt_s: float) -> EnergySnapshot:
        comps: dict[str, float] = {}
        rpm = float(sensors.get("rpm") or 0)
        if actuators.get("engine"):
            comps["motor"] = P0_ENGINE_W + K_RPM * rpm
            if actuators.get("sport_mode"):
                comps["motor"] *= 1.35
        else:
            comps["motor"] = 0.0
        comps["headlight"] = P_HEADLIGHT_W if actuators.get("headlight") else 0.0
        comps["sound"] = P_SOUND_W if actuators.get("sound") else 0.0
        comps["climate"] = P_CLIMATE_W if actuators.get("climate") else 0.0
        comps["track"] = P_TRACK_W if actuators.get("tracking") else 0.0
        comps["spoiler"] = P_SPOILER_W if actuators.get("spoiler") else 0.0
        total = sum(comps.values())
        dt_h = max(0.0, dt_s) / 3600.0
        bat = float(sensors.get("battery") or 100)
        fuel = float(sensors.get("fuel") or 100)
        # battery % from Wh
        d_wh = total * dt_h
        bat = max(5.0, bat - 100.0 * d_wh / BATTERY_CAPACITY_WH)
        fuel = max(1.0, fuel - FUEL_ALPHA * comps["motor"] * dt_h * 1000)
        return EnergySnapshot(power_w=total, battery_pct=bat, fuel_pct=fuel, components=comps)


energy_model = EnergyModel()
