"""Append-only audit log with SHA-256 hash chain."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from schemas import utc_now_iso


class AuditLog:
    def __init__(self, log_path: Optional[str] = None) -> None:
        if log_path is None:
            base = Path(__file__).resolve().parents[2] / "data"
            base.mkdir(parents=True, exist_ok=True)
            self.path = base / "audit.jsonl"
        else:
            self.path = Path(log_path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        last_line = ""
        try:
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        last_line = line.strip()
            if last_line:
                obj = json.loads(last_line)
                return obj.get("hash", "0" * 64)
        except Exception:
            pass
        return "0" * 64

    def log(self, event_type: str, agent: str, data: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = utc_now_iso()
        payload = {
            "timestamp": timestamp,
            "event_type": event_type,
            "agent": agent,
            "data": data,
            "prev_hash": self._last_hash,
        }
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        payload["hash"] = digest
        self._last_hash = digest
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")
        return payload

    def append(self, event_type: str, agent: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.log(event_type, agent, data)

    def read_all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
        return entries
