"""Camada de banco — Ferrari IoT."""

from datetime import datetime
import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from config import settings
from models import ActionLog, Base, Device, TelemetrySample, User

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DEFAULT_DEVICES = [
    {"device_id": "arduino-ferrari", "name": "Arduino Ferrari Node", "kind": "arduino", "status": "online"},
    {"device_id": "raspberry-hub", "name": "Raspberry Pi Hub", "kind": "raspberry", "status": "online"},
    {"device_id": "door-driver", "name": "Porta Motorista", "kind": "door", "status": "closed"},
    {"device_id": "door-passenger", "name": "Porta Passageiro", "kind": "door", "status": "closed"},
    {"device_id": "roof", "name": "Teto Retrátil", "kind": "roof", "status": "closed"},
    {"device_id": "engine", "name": "Motor V8", "kind": "engine", "status": "off"},
    {"device_id": "sound", "name": "Sistema de Som", "kind": "sound", "status": "off"},
    {"device_id": "headlight", "name": "Faróis LED", "kind": "light", "status": "off"},
    {"device_id": "tracker", "name": "GPS Tracker", "kind": "gps", "status": "idle"},
    {"device_id": "alarm", "name": "Alarme", "kind": "alarm", "status": "armed"},
    {"device_id": "spoiler", "name": "Aerofólio Ativo", "kind": "spoiler", "status": "retracted"},
    {"device_id": "climate", "name": "Climatização", "kind": "climate", "status": "off"},
]

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == settings.admin_user).first():
            db.add(User(username=settings.admin_user, password_hash=hash_password(settings.admin_password)))
        for item in DEFAULT_DEVICES:
            if not db.query(Device).filter(Device.device_id == item["device_id"]).first():
                db.add(Device(**item, last_seen=datetime.utcnow()))
        if db.query(TelemetrySample).count() == 0:
            db.add(TelemetrySample(rpm=800, speed_kmh=0, engine_temp=78, lat=-23.5505, lon=-46.6333))
        db.commit()
    finally:
        db.close()

def log_action(db: Session, device: str, action: str, detail: str = "") -> ActionLog:
    entry = ActionLog(device=device, action=action, detail=detail)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def touch_device(db: Session, device_id: str, status: str | None = None) -> Device | None:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        return None
    device.last_seen = datetime.utcnow()
    if status is not None:
        device.status = status
    db.commit()
    return device
