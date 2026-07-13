"""
Integridade criptográfica: HMAC-SHA256 nos comandos + cadeia hash de auditoria.
"""

from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

SECRET = os.getenv("FERRARI_HMAC_SECRET", "ferrari-postdoc-hmac-secret-v1").encode("utf-8")


def sign_payload(payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return {**payload, "hmac": sig, "signed_at": time.time()}


def verify_payload(payload: dict[str, Any]) -> bool:
    if "hmac" not in payload:
        return False
    copy = {k: v for k, v in payload.items() if k not in ("hmac",)}
    # signed_at is part of signed material when present after sign — verify against fields except hmac
    expected = sign_payload({k: v for k, v in copy.items() if k != "signed_at"})
    # Re-sign without signed_at drift: compare hmac of canonical without hmac/signed_at
    body = json.dumps({k: v for k, v in payload.items() if k not in ("hmac", "signed_at")}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, payload["hmac"])


@dataclass
class AuditChain:
    entries: list[dict[str, Any]] = field(default_factory=list)
    genesis: str = field(default_factory=lambda: hashlib.sha256(b"ferrari-genesis").hexdigest())

    def append(self, event: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        prev = self.entries[-1]["hash"] if self.entries else self.genesis
        record = {
            "seq": len(self.entries) + 1,
            "ts": time.time(),
            "event": event,
            "detail": detail or {},
            "prev_hash": prev,
        }
        blob = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        record["hash"] = hashlib.sha256(blob).hexdigest()
        signed = sign_payload({"seq": record["seq"], "event": event, "hash": record["hash"], "prev_hash": prev})
        record["hmac"] = signed["hmac"]
        self.entries.append(record)
        return record

    def verify_chain(self) -> dict[str, Any]:
        prev = self.genesis
        for i, e in enumerate(self.entries):
            if e["prev_hash"] != prev:
                return {"ok": False, "broken_at": i, "reason": "prev_hash mismatch"}
            check = {k: v for k, v in e.items() if k not in ("hash", "hmac")}
            blob = json.dumps(check, sort_keys=True, separators=(",", ":")).encode("utf-8")
            if hashlib.sha256(blob).hexdigest() != e["hash"]:
                return {"ok": False, "broken_at": i, "reason": "hash mismatch"}
            prev = e["hash"]
        return {"ok": True, "length": len(self.entries), "tip": prev if self.entries else self.genesis}

    def tip(self) -> str:
        return self.entries[-1]["hash"] if self.entries else self.genesis


audit_chain = AuditChain()
audit_chain.append("BOOT", {"app": "Ferrari IoT Postdoc"})
