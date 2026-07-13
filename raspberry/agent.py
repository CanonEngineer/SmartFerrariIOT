"""Agente Raspberry — Ferrari IoT edge hub."""
from __future__ import annotations
import json, logging, os, signal, sys, threading, time
import requests
from actuators import Actuators

logging.basicConfig(level=logging.INFO, format="%(asctime)s [raspberry-ferrari] %(message)s")
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8001")
USE_MQTT = os.getenv("USE_MQTT", "0") == "1"
MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
actuators = Actuators()
_stop = threading.Event()

def heartbeat_loop():
    while not _stop.is_set():
        try:
            requests.post(f"{API_BASE}/api/heartbeat", json={"board": "raspberry"}, timeout=2)
        except Exception:
            pass
        _stop.wait(2.0)

def poll_api():
    last = None
    while not _stop.is_set():
        try:
            data = requests.get(f"{API_BASE}/api/status", timeout=2).json().get("state", {})
            act = data.get("actuators", {})
            blob = json.dumps(act, sort_keys=True)
            if blob != last:
                last = blob
                actuators.mirror(act)
                logging.info("Estado espelhado")
        except Exception as exc:
            logging.debug("%s", exc)
        _stop.wait(1.0)

def main():
    signal.signal(signal.SIGINT, lambda *_: _stop.set())
    signal.signal(signal.SIGTERM, lambda *_: _stop.set())
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    if USE_MQTT:
        try:
            import paho.mqtt.client as mqtt
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="raspberry-ferrari")
            def on_connect(c, u, f, rc, p=None):
                for t in ("ferrari/door", "ferrari/roof", "ferrari/engine", "ferrari/sound", "ferrari/headlight", "ferrari/track"):
                    c.subscribe(t)
            def on_message(c, u, msg):
                try:
                    payload = json.loads(msg.payload.decode())
                except Exception:
                    payload = {}
                actuators.apply_topic(msg.topic, payload)
                c.publish("ferrari/sync", json.dumps({"board": "raspberry", "ok": True}))
            client.on_connect = on_connect
            client.on_message = on_message
            client.connect(MQTT_HOST, 1883, 60)
            client.loop_start()
            while not _stop.is_set():
                client.publish("ferrari/sync", json.dumps({"board": "raspberry", "ok": True}))
                _stop.wait(1.5)
            client.loop_stop()
            return
        except Exception as exc:
            logging.warning("MQTT falhou (%s) — API poll", exc)
    poll_api()

if __name__ == "__main__":
    main()
