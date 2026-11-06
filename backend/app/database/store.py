from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class EventStore:
    def __init__(self, path: str = "climascope.db") -> None:
        self.path = Path(path)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS alert_events (id INTEGER PRIMARY KEY, location TEXT, event_type TEXT, severity TEXT, payload TEXT, detected_at TEXT DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.commit()

    def record_alerts(self, location: str, alerts: list[dict[str, Any]]) -> None:
        with sqlite3.connect(self.path) as connection:
            for alert in alerts:
                connection.execute(
                    "INSERT INTO alert_events(location,event_type,severity,payload) VALUES(?,?,?,?)",
                    (location, alert["event_type"], alert["severity"], json.dumps(alert)),
                )
            connection.commit()
