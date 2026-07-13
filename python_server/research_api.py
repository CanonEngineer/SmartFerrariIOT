from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db, log_action
from experiments import experiment_runner
from protocol import ARCHITECTURE_LAYERS, PROTOCOL_VERSION, TOPIC_SCHEMA
from telemetry import telemetry
from hil import hil
from security import audit_chain
from statemachine import digital_twin
from paperpack import build_paper_pack
from state import ferrari_state

router = APIRouter(prefix="/api/research", tags=["research"])

class ExperimentBody(BaseModel):
    name: str
    params: dict = Field(default_factory=dict)

class HILBody(BaseModel):
    enabled: bool | None = None
    delay_ms: float | None = None
    loss_rate: float | None = None

class VisionEvent(BaseModel):
    kind: str  # gesture_start | qr_track
    confidence: float = 1.0
    detail: str = ""

@router.get("/overview")
def overview():
    snap = ferrari_state.snapshot()
    return {
        "title": "Ferrari IoT — Postdoc Research Lab",
        "protocol_version": PROTOCOL_VERSION,
        "architecture_layers": ARCHITECTURE_LAYERS,
        "topics": TOPIC_SCHEMA,
        "experiments": experiment_runner.CATALOG,
        "telemetry": telemetry.summary(),
        "twin": snap.get("twin"),
        "energy": snap.get("energy"),
        "hil": snap.get("hil"),
        "audit": audit_chain.verify_chain(),
    }

@router.get("/telemetry")
def get_telemetry():
    return telemetry.summary()

@router.get("/twin")
def twin():
    digital_twin.bind(ferrari_state.actuators, ferrari_state.sensors)
    return digital_twin.ctx.snapshot()

@router.get("/energy")
def energy():
    return ferrari_state.energy

@router.get("/hil")
def get_hil():
    return hil.snapshot()

@router.post("/hil")
def set_hil(body: HILBody):
    return hil.configure(delay_ms=body.delay_ms, loss_rate=body.loss_rate, enabled=body.enabled)

@router.get("/audit")
def audit(limit: int = 50):
    return {
        "verify": audit_chain.verify_chain(),
        "entries": audit_chain.entries[-min(limit, 200):],
    }

@router.get("/experiments")
def list_experiments():
    return {
        "catalog": experiment_runner.CATALOG,
        "history": [
            {"experiment_id": e.experiment_id, "name": e.name, "sqi": e.metrics.get("sync_quality_index"),
             "started_at": e.started_at}
            for e in experiment_runner.history[-30:]
        ],
    }

@router.post("/experiments/run")
async def run_experiment(body: ExperimentBody, db: Session = Depends(get_db)):
    try:
        result = await experiment_runner.run(body.name, db, body.params)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "result": result.to_dict()}

@router.get("/experiments/{experiment_id}/export.csv")
def export_csv(experiment_id: str):
    try:
        bundle = experiment_runner.export_bundle(experiment_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return FileResponse(bundle["csv_path"], media_type="text/csv", filename=f"{experiment_id}.csv")

@router.get("/experiments/{experiment_id}/export.json")
def export_json(experiment_id: str):
    try:
        bundle = experiment_runner.export_bundle(experiment_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return FileResponse(bundle["json_path"], media_type="application/json", filename=f"{experiment_id}.json")

@router.post("/paper-pack")
def paper_pack():
    snap = ferrari_state.snapshot()
    path = build_paper_pack(
        [e.to_dict() for e in experiment_runner.history],
        snap.get("twin") or {},
        snap.get("energy") or {},
        snap.get("hil") or {},
        audit_chain.verify_chain(),
    )
    return {"ok": True, "path": str(path), "download": "/api/research/paper-pack.tex"}

@router.get("/paper-pack.tex")
def download_paper_pack():
    path = build_paper_pack(
        [e.to_dict() for e in experiment_runner.history],
        ferrari_state.snapshot().get("twin") or {},
        ferrari_state.energy,
        hil.snapshot(),
        audit_chain.verify_chain(),
    )
    return FileResponse(path, media_type="application/x-tex", filename="ferrari_paper_pack.tex")

@router.post("/vision/event")
async def vision_event(body: VisionEvent, db: Session = Depends(get_db)):
    log_action(db, "vision", body.kind, f"{body.detail}|c={body.confidence}")
    if body.kind == "gesture_start":
        await ferrari_state.set_alarm(False)
        await ferrari_state.set_lock(False)
        await ferrari_state.set_engine(True)
    elif body.kind == "qr_track":
        await ferrari_state.set_tracking(True)
    return {"ok": True, "state": ferrari_state.snapshot()}

@router.get("/thesis-brief.md", response_class=PlainTextResponse)
def thesis_brief():
    t = telemetry.summary()
    snap = ferrari_state.snapshot()
    return (
        "# Ferrari IoT Postdoc — Brief Técnico\n\n"
        f"- Protocolo: {PROTOCOL_VERSION}\n"
        f"- Twin mode: {(snap.get('twin') or {}).get('mode')}\n"
        f"- SQI: {t['sync_quality_index']}\n"
        f"- Power: {(snap.get('energy') or {}).get('power_w')} W\n"
        f"- HIL: {hil.snapshot()['qos']}\n"
        f"- Audit: {audit_chain.verify_chain()}\n"
    )
