"""Atuadores Ferrari no edge (GPIO real ou stub)."""
from __future__ import annotations
import logging
logger = logging.getLogger("ferrari-actuators")

class Actuators:
    def __init__(self):
        self.state = {}

    def mirror(self, act: dict) -> None:
        self.state = act
        logger.info(
            "doors=%s roof=%s engine=%s sound=%s hl=%s track=%s",
            act.get("door"), act.get("roof"), act.get("engine"),
            act.get("sound"), act.get("headlight"), act.get("tracking"),
        )

    def apply_topic(self, topic: str, payload: dict) -> None:
        logger.info("MQTT %s %s", topic, payload)
