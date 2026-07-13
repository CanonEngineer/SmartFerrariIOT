"""Ferrari IoT Postdoc Platform — servidor principal (porta 8001)."""

from __future__ import annotations
import asyncio, logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from api import router as api_router
from config import settings
from database import SessionLocal, init_db
from mqtt_bridge import mqtt_bridge
from protocol import PROTOCOL_VERSION
from research_api import router as research_router
from simulator import simulator
from state import ferrari_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ferrari")
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

def handle_mqtt_message(topic: str, payload: dict) -> None:
    async def _apply() -> None:
        if topic == "ferrari/sync" and payload.get("board") in ("arduino", "raspberry"):
            await ferrari_state.heartbeat(payload["board"])
        elif topic == "ferrari/rpm" and "value" in payload:
            await ferrari_state.update_sensors(rpm=float(payload["value"]))
        elif topic == "ferrari/speed" and "value" in payload:
            await ferrari_state.update_sensors(speed_kmh=float(payload["value"]))
        elif topic == "ferrari/temp" and "value" in payload:
            await ferrari_state.update_sensors(engine_temp=float(payload["value"]))
        elif topic == "ferrari/gps":
            await ferrari_state.update_sensors(lat=float(payload.get("lat", 0)), lon=float(payload.get("lon", 0)))
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_apply())
    except RuntimeError:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    mqtt_bridge.configure(handle_mqtt_message)
    mqtt_bridge.start()
    await simulator.start(SessionLocal)
    logger.info("Ferrari Lab online em http://%s:%s", settings.host, settings.port)
    yield
    await simulator.stop()
    mqtt_bridge.stop()

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)
app.include_router(research_router)
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

@app.get("/")
def index():
    path = WEB_DIR / "index.html"
    return FileResponse(path) if path.exists() else {"message": "web/index.html ausente"}

@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "protocol": PROTOCOL_VERSION}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.host, port=settings.port, reload=False)
