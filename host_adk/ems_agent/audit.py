"""Append-only dispatch audit trail (JSONL).

Every A2A dispatch, response, and decision gets one line with timestamps and
durations - this is both the medical-domain audit record and the evidence for
the 1-minute-decision KPI.

Contains patient information: the file lives outside the repo by default
(AMBULANCE_DATA_DIR, ~/.ambulance if unset) and must be protected accordingly.
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _default_path() -> Path:
    data_dir = Path(os.getenv("AMBULANCE_DATA_DIR", "~/.ambulance")).expanduser()
    return data_dir / "dispatch_audit.jsonl"


class AuditLog:
    def __init__(self, path: Path | None = None):
        self._path = path or _default_path()
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, **fields) -> None:
        """Append one event line. Never raises - auditing must not break dispatch."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        try:
            line = json.dumps(entry, ensure_ascii=False)
            with self._lock, self._path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.error("Failed to write audit entry %s: %s", event, e)


audit_log = AuditLog()
