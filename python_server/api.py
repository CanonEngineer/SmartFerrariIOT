"""API REST + WebSocket — Ferrari IoT."""

from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from auth import authenticate_user, create_access_token, get_current_user
from database import SessionLocal, get_db, log_action, touch_device
from models import ActionLog, Device, TelemetrySample, User
from mqtt_bridge import mqtt_bridge
from protocol import PROTOCOL_VERSION
from simulator import simulator
from state import ferrari_state
from telemetry import telemetry
from statemachine import InvariantViolation
from security import audit_chain, sign_payload, verify_payload
from hil import hil


router = APIRouter(prefix="/api")

class BoolBody(BaseModel):
    on: bool

class DoorBody(BaseModel):
    door_id: str = Field(..., pattern=r"^(driver|passenger)$")
    open: bool

class SimulateBody(BaseModel):
    scenario: str = "startup"

class HeartbeatBody(BaseModel):
    board: str

@router.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form.username, form.password)
    if not user:
        raise HTTPException(401, "Credenciais inválidas")
    return {"access_token": create_access_token(user.username), "token_type": "bearer"}

@router.get("/status")
async def status():
    return {
        "ok": True,
        "protocol_version": PROTOCOL_VERSION,
        "mqtt_connected": mqtt_bridge.connected,
        "state": ferrari_state.snapshot(),
        "telemetry": telemetry.summary(),
    }

@router.get("/devices")
def devices(db: Session = Depends(get_db)):
    return [
        {"device_id": d.device_id, "name": d.name, "kind": d.kind, "status": d.status,
         "last_seen": d.last_seen.isoformat() if d.last_seen else None}
        for d in db.query(Device).order_by(Device.id).all()
    ]

@router.get("/logs")
def logs(db: Session = Depends(get_db), limit: int = 80):
    rows = db.query(ActionLog).order_by(ActionLog.timestamp.desc()).limit(min(limit, 300)).all()
    return [{"device": r.device, "action": r.action, "detail": r.detail,
             "timestamp": r.timestamp.isoformat() if r.timestamp else None} for r in rows]

@router.get("/telemetry/history")
def telemetry_history(db: Session = Depends(get_db), limit: int = 50):
    rows = db.query(TelemetrySample).order_by(TelemetrySample.created_at.desc()).limit(min(limit, 200)).all()
    return [{"rpm": r.rpm, "speed_kmh": r.speed_kmh, "engine_temp": r.engine_temp,
             "lat": r.lat, "lon": r.lon, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]

async def _act(db, device_id, action, detail, coro, mqtt_topic, mqtt_payload):
    try:
        state = await coro
    except InvariantViolation as exc:
        raise HTTPException(409, detail={"code": exc.code, "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    touch_device(db, device_id, detail)
    log_action(db, device_id, action, detail)
    signed = sign_payload(mqtt_payload)
    mqtt_bridge.publish(mqtt_topic, signed)
    return {"ok": True, "state": state, "signed": signed, "audit_tip": audit_chain.tip()}


@router.post("/door")
async def door(body: DoorBody, db: Session = Depends(get_db)):
    return await _act(db, f"door-{body.door_id}", "door", "open" if body.open else "closed",
                      ferrari_state.set_door(body.door_id, body.open),
                      "ferrari/door", {"door_id": body.door_id, "open": body.open})

@router.post("/roof")
async def roof(body: BoolBody, db: Session = Depends(get_db)):
    return await _act(db, "roof", "roof", "open" if body.on else "closed",
                      ferrari_state.set_roof(body.on), "ferrari/roof", {"open": body.on})

@router.post("/engine")
async def engine(body: BoolBody, db: Session = Depends(get_db)):
    return await _act(db, "engine", "engine", "on" if body.on else "off",
                      ferrari_state.set_engine(body.on), "ferrari/engine", {"on": body.on})

@router.post("/sound")
async def sound(body: BoolBody, db: Session = Depends(get_db)):
    return await _act(db, "sound", "sound", "on" if body.on else "off",
                      ferrari_state.set_sound(body.on), "ferrari/sound", {"on": body.on})

@router.post("/headlight")
async def headlight(body: BoolBody, db: Session = Depends(get_db)):
    return await _act(db, "headlight", "headlight", "on" if body.on else "off",
                      ferrari_state.set_headlight(body.on), "ferrari/headlight", {"on": body.on})

@router.post("/track")
async def track(body: BoolBody, db: Session = Depends(get_db)):
    return await _act(db, "tracker", "track", "on" if body.on else "off",
                      ferrari_state.set_tracking(body.on), "ferrari/track", {"on": body.on})

@router.post("/alarm")
async def alarm(body: BoolBody, db: Session = Depends(get_db)):
    return await _act(db, "alarm", "alarm", "armed" if body.on else "disarmed",
                      ferrari_state.set_alarm(body.on), "ferrari/alarm", {"armed": body.on})

@router.post("/spoiler")
async def spoiler(body: BoolBody, db: Session = Depends(get_db)):
    return await _act(db, "spoiler", "spoiler", "out" if body.on else "in",
                      ferrari_state.set_spoiler(body.on), "ferrari/spoiler", {"deployed": body.on})

@router.post("/climate")
async def climate(body: BoolBody, db: Session = Depends(get_db)):
    return await _act(db, "climate", "climate", "on" if body.on else "off",
                      ferrari_state.set_climate(body.on), "ferrari/climate", {"on": body.on})

@router.post("/horn")
async def horn(body: BoolBody, db: Session = Depends(get_db)):
    return await _act(db, "horn", "horn", "on" if body.on else "off",
                      ferrari_state.set_horn(body.on), "ferrari/horn", {"on": body.on})

@router.post("/sport")
async def sport(body: BoolBody, db: Session = Depends(get_db)):
    return await _act(db, "engine", "sport", "on" if body.on else "off",
                      ferrari_state.set_sport_mode(body.on), "ferrari/sport", {"on": body.on})

@router.post("/lock")
async def lock(body: BoolBody, db: Session = Depends(get_db)):
    return await _act(db, "door-driver", "lock", "on" if body.on else "off",
                      ferrari_state.set_lock(body.on), "ferrari/lock", {"locked": body.on})

@router.post("/simulate")
async def simulate(body: SimulateBody, db: Session = Depends(get_db)):
    try:
        return await simulator.run_scenario(body.scenario, db)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@router.post("/heartbeat")
async def heartbeat(body: HeartbeatBody, db: Session = Depends(get_db)):
    try:
        state = await ferrari_state.heartbeat(body.board)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    touch_device(db, {"arduino": "arduino-ferrari", "raspberry": "raspberry-hub"}.get(body.board, body.board), "online")
    return {"ok": True, "state": state}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "state", "data": ferrari_state.snapshot()})

    async def forward(payload: dict[str, Any]) -> None:
        await websocket.send_json(payload)

    ferrari_state.add_listener(forward)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            try:
                if action == "door":
                    await ferrari_state.set_door(str(data.get("door_id", "driver")), bool(data.get("open")))
                elif action == "roof":
                    await ferrari_state.set_roof(bool(data.get("on", data.get("open"))))
                elif action == "engine":
                    await ferrari_state.set_engine(bool(data.get("on")))
                elif action == "sound":
                    await ferrari_state.set_sound(bool(data.get("on")))
                elif action == "headlight":
                    await ferrari_state.set_headlight(bool(data.get("on")))
                elif action == "track":
                    await ferrari_state.set_tracking(bool(data.get("on")))
                elif action == "alarm":
                    await ferrari_state.set_alarm(bool(data.get("on")))
                elif action == "spoiler":
                    await ferrari_state.set_spoiler(bool(data.get("on")))
                elif action == "climate":
                    await ferrari_state.set_climate(bool(data.get("on")))
                elif action == "horn":
                    await ferrari_state.set_horn(bool(data.get("on")))
                elif action == "sport":
                    await ferrari_state.set_sport_mode(bool(data.get("on")))
                elif action == "lock":
                    await ferrari_state.set_lock(bool(data.get("on")))
                elif action == "simulate":
                    db = SessionLocal()
                    try:
                        await simulator.run_scenario(str(data.get("scenario", "startup")), db)
                    finally:
                        db.close()
                elif action == "ping":
                    await websocket.send_json({"type": "pong", "ts": datetime.utcnow().isoformat()})
            except InvariantViolation as exc:
                await websocket.send_json({
                    "type": "invariant_violation",
                    "invariant": exc.code,
                    "message": str(exc),
                })
            except ValueError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
    except WebSocketDisconnect:
        pass
    finally:
        ferrari_state.remove_listener(forward)
