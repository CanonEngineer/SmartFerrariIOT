"""Protocolo Ferrari IoT v1.0.0 — pós-doutorado."""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field

PROTOCOL_VERSION = "1.0.0"
NAMESPACE = "ferrari"

class QoSLevel(int, Enum):
    AT_MOST_ONCE = 0
    AT_LEAST_ONCE = 1
    EXACTLY_ONCE = 2

class Envelope(BaseModel):
    protocol: str = PROTOCOL_VERSION
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    qos: QoSLevel = QoSLevel.AT_LEAST_ONCE
    payload: dict[str, Any]

TOPIC_SCHEMA = {
    f"{NAMESPACE}/rpm": {"direction": "device→edge", "payload": "SensorPayload"},
    f"{NAMESPACE}/speed": {"direction": "device→edge", "payload": "SensorPayload"},
    f"{NAMESPACE}/temp": {"direction": "device→edge", "payload": "SensorPayload"},
    f"{NAMESPACE}/gps": {"direction": "device→edge", "payload": "GpsPayload"},
    f"{NAMESPACE}/door": {"direction": "edge→device", "payload": "ActuatorCommand"},
    f"{NAMESPACE}/roof": {"direction": "edge→device", "payload": "ActuatorCommand"},
    f"{NAMESPACE}/engine": {"direction": "edge→device", "payload": "ActuatorCommand"},
    f"{NAMESPACE}/sound": {"direction": "edge→device", "payload": "ActuatorCommand"},
    f"{NAMESPACE}/headlight": {"direction": "edge→device", "payload": "ActuatorCommand"},
    f"{NAMESPACE}/track": {"direction": "edge→device", "payload": "ActuatorCommand"},
    f"{NAMESPACE}/sync": {"direction": "bidirectional", "payload": "SyncHeartbeat"},
}

ARCHITECTURE_LAYERS = [
    {"id": "L1", "name": "Percepção / Atuação veicular", "components": ["Arduino/ESP32", "Servos porta/teto", "Relés farol/som", "GPS", "RPM"]},
    {"id": "L2", "name": "Comunicação", "components": ["Wi-Fi", "MQTT ferrari/*", "REST", "WebSocket"]},
    {"id": "L3", "name": "Edge Coordination", "components": ["Raspberry Pi Hub", "Espelhamento", "Heartbeat sync"]},
    {"id": "L4", "name": "Serviço / Persistência", "components": ["FastAPI", "SQLite", "Telemetria SQI", "Auditoria"]},
    {"id": "L5", "name": "Experimentação", "components": ["Simulador Ferrari", "Research Lab", "Export CSV/JSON"]},
]

def wrap(source: str, payload: dict[str, Any]) -> dict[str, Any]:
    return Envelope(source=source, payload=payload).model_dump(mode="json")
