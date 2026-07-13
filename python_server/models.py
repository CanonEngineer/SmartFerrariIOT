from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True)
    device_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    kind = Column(String(32), nullable=False)
    status = Column(String(32), default="offline")
    last_seen = Column(DateTime, default=datetime.utcnow)

class TelemetrySample(Base):
    __tablename__ = "telemetry"
    id = Column(Integer, primary_key=True)
    rpm = Column(Float, default=0)
    speed_kmh = Column(Float, default=0)
    engine_temp = Column(Float, default=0)
    lat = Column(Float, default=0)
    lon = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class ActionLog(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    device = Column(String(64), nullable=False)
    action = Column(String(128), nullable=False)
    detail = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
