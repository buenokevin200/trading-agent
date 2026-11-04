"""Append-only audit log — application-level, with tamper detection."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import json
import os
import hashlib
import logging

logger = logging.getLogger(__name__)


class AuditLog:
    """
    Append-only audit log stored as JSONL file.
    Each entry is hashed with the previous entry's hash for chain integrity.
    Tamper detection: re-hash the chain and compare.
    """

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w") as f:
                pass  # create empty

    def append(self, event_type: str, data: dict[str, Any], agent: str = "system") -> str:
        """Append an event to the audit log."""
        prev_hash = self._last_hash()
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "agent": agent,
            "data": data,
            "prev_hash": prev_hash,
        }
        entry_hash = self._compute_hash(entry)
        entry["hash"] = entry_hash

        with open(self.path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

        logger.debug(f"Audit: {event_type} by {agent} — hash={entry_hash[:8]}")
        return entry_hash

    def verify_chain(self) -> tuple[bool, list[str]]:
        """Verify the integrity of the audit chain. Returns (ok, errors)."""
        errors = []
        prev_hash = ""
        with open(self.path, "r") as f:
            for i, line in enumerate(f):
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"Line {i}: invalid JSON")
                    continue
                if entry.get("prev_hash") != prev_hash:
                    errors.append(f"Line {i}: hash chain broken")
                recomputed = self._compute_hash(entry)
                if recomputed != entry.get("hash"):
                    errors.append(f"Line {i}: hash mismatch (tampered)")
                prev_hash = entry.get("hash", "")
        return (len(errors) == 0, errors)

    def read_all(self) -> list[dict]:
        """Read all entries."""
        entries = []
        with open(self.path, "r") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries

    def _last_hash(self) -> str:
        """Get the hash of the last entry in the log."""
        try:
            with open(self.path, "r") as f:
                lines = f.readlines()
            # Filter out empty lines
            lines = [l for l in lines if l.strip()]
            if not lines:
                return ""
            return json.loads(lines[-1]).get("hash", "")
        except (FileNotFoundError, json.JSONDecodeError, KeyError, IndexError):
            return ""

    @staticmethod
    def _compute_hash(entry: dict) -> str:
        """Compute SHA-256 hash of entry (without the hash field itself)."""
        copy = {k: v for k, v in entry.items() if k != "hash"}
        return hashlib.sha256(
            json.dumps(copy, sort_keys=True, default=str).encode()
        ).hexdigest()
