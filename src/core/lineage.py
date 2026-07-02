"""
Data Lineage & Audit Trail Module.

Every data transformation in the pipeline is logged with:
  Who | What | When | Before | After | Reason

This enables full audit transparency for CPAs and Medicare compliance.
Lineage entries are persisted as JSONL files in the lineage log directory.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.config import settings
from src.core.models import LineageEntry


class LineageLogger:
    """
    Logger for audit trail entries.

    Each entry records a single state-changing action with full provenance.
    Entries are written as JSONL (one JSON object per line) for easy
    searching, filtering, and export.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or settings.LINEAGE_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._session_id: str = uuid.uuid4().hex[:12]
        self._buffer: list[LineageEntry] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        actor: str = "system",
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        reason: Optional[str] = None,
    ) -> LineageEntry:
        """Create and record a lineage entry."""
        entry = LineageEntry(
            action=action,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            reason=reason,
            session_id=self._session_id,
        )
        self._buffer.append(entry)
        self._flush(entry)
        return entry

    def log_import(
        self,
        source_file: str,
        row_count: int,
        error_count: int,
        ingestion_id: str,
        actor: str = "system",
    ) -> LineageEntry:
        """Log a file import event."""
        return self.log(
            action="import",
            entity_type="ingestion",
            entity_id=ingestion_id,
            actor=actor,
            after_state={
                "source_file": source_file,
                "row_count": row_count,
                "error_count": error_count,
            },
            reason=f"Imported {row_count} rows from {source_file} ({error_count} errors)",
        )

    def log_classification(
        self,
        transaction_id: str,
        account_number: str,
        from_center: Optional[str],
        to_center: str,
        confidence: float,
        actor: str = "ai",
        reason: Optional[str] = None,
    ) -> LineageEntry:
        """Log a single classification event."""
        before = {"cost_center": from_center} if from_center else None
        after = {
            "cost_center": to_center,
            "confidence": confidence,
            "actor": actor,
        }
        return self.log(
            action="classify" if actor == "ai" else "override",
            entity_type="classification",
            entity_id=transaction_id,
            actor=actor,
            before_state=before,
            after_state=after,
            reason=reason or f"Account {account_number} classified to {to_center}",
        )

    def log_export(
        self,
        export_id: str,
        format: str,
        facility_type: str,
        row_count: int,
        actor: str = "system",
    ) -> LineageEntry:
        """Log an export event."""
        return self.log(
            action="export",
            entity_type="export",
            entity_id=export_id,
            actor=actor,
            after_state={
                "format": format,
                "facility_type": facility_type,
                "row_count": row_count,
            },
            reason=f"Exported {row_count} rows as {format} for {facility_type}",
        )

    def get_session_trail(self, session_id: Optional[str] = None) -> list[LineageEntry]:
        """Retrieve all lineage entries for a session."""
        sid = session_id or self._session_id
        session_file = self.log_dir / f"session_{sid}.jsonl"
        if not session_file.exists():
            return []
        entries: list[LineageEntry] = []
        with open(session_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    entries.append(LineageEntry(**data))
                except (json.JSONDecodeError, Exception):
                    continue
        return entries

    def get_all_entries(self, limit: int = 1000) -> list[LineageEntry]:
        """Retrieve all lineage entries across all sessions."""
        entries: list[LineageEntry] = []
        for f in sorted(self.log_dir.glob("session_*.jsonl")):
            with open(f, "r") as fh:
                for line in fh:
                    try:
                        entries.append(LineageEntry(**json.loads(line)))
                    except Exception:
                        continue
                    if len(entries) >= limit:
                        return entries
        return entries

    def export_trail_to_csv(self, output_path: Path) -> None:
        """Export the full audit trail as CSV for compliance review."""
        import csv

        entries = self.get_all_entries()
        if not entries:
            return

        fieldnames = [
            "id", "timestamp", "action", "actor", "entity_type",
            "entity_id", "reason", "session_id",
        ]
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for e in entries:
                writer.writerow({
                    "id": e.id,
                    "timestamp": e.timestamp.isoformat(),
                    "action": e.action,
                    "actor": e.actor,
                    "entity_type": e.entity_type,
                    "entity_id": e.entity_id,
                    "reason": e.reason or "",
                    "session_id": e.session_id or "",
                })

    def _flush(self, entry: LineageEntry) -> None:
        """Write a single entry to the JSONL session file."""
        if not settings.LINEAGE_ENABLED:
            return
        session_file = self.log_dir / f"session_{self._session_id}.jsonl"
        with open(session_file, "a") as f:
            f.write(entry.model_dump_json() + "\n")
