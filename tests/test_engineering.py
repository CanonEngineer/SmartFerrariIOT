import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python_server"))
from protocol import PROTOCOL_VERSION, TOPIC_SCHEMA
from telemetry import TelemetryEngine

def test_protocol():
    assert PROTOCOL_VERSION == "1.0.0"
    assert "ferrari/sync" in TOPIC_SCHEMA

def test_sqi():
    e = TelemetryEngine()
    e.record_heartbeat("arduino")
    e.record_heartbeat("raspberry")
    assert 0 <= e.sync_quality_index() <= 100

if __name__ == "__main__":
    test_protocol()
    test_sqi()
    print("OK Ferrari engineering tests")
