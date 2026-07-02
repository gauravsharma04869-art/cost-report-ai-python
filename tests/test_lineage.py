"""
Tests for the data lineage / audit trail module.
"""

from pathlib import Path

import pytest

from src.core.lineage import LineageLogger
from src.core.models import LineageEntry


@pytest.fixture
def logger(tmp_path: Path):
    """Create a LineageLogger with a temporary log directory."""
    return LineageLogger(log_dir=tmp_path)


class TestLineageLogger:
    def test_log_basic(self, logger: LineageLogger):
        entry = logger.log(
            action="import",
            entity_type="ingestion",
            entity_id="test123",
            actor="system",
            after_state={"file": "test.csv", "rows": 100},
            reason="Imported 100 rows",
        )
        assert entry.action == "import"
        assert entry.actor == "system"
        assert entry.session_id == logger.session_id
        assert entry.entity_id == "test123"

    def test_log_import(self, logger: LineageLogger):
        entry = logger.log_import(
            source_file="test.csv",
            row_count=100,
            error_count=2,
            ingestion_id="ing123",
        )
        assert entry.action == "import"
        assert entry.after_state["row_count"] == 100

    def test_log_classification(self, logger: LineageLogger):
        entry = logger.log_classification(
            transaction_id="txn123",
            account_number="6010",
            from_center=None,
            to_center="20",
            confidence=0.95,
        )
        assert entry.action == "classify"
        assert entry.after_state["cost_center"] == "20"

    def test_log_override(self, logger: LineageLogger):
        entry = logger.log_classification(
            transaction_id="txn123",
            account_number="6010",
            from_center="04",
            to_center="20",
            confidence=0.95,
            actor="gaura.cpa",
            reason="Manual override: this is a nursing cost, not A&G",
        )
        assert entry.action == "override"
        assert entry.actor == "gaura.cpa"
        assert entry.before_state["cost_center"] == "04"

    def test_log_export(self, logger: LineageLogger):
        entry = logger.log_export(
            export_id="exp123",
            format="xlsx",
            facility_type="hospital",
            row_count=150,
        )
        assert entry.action == "export"

    def test_session_trail(self, logger: LineageLogger):
        logger.log_import("test.csv", 100, 0, "ing1")
        logger.log_import("data2.csv", 50, 1, "ing2")

        entries = logger.get_session_trail(logger.session_id)
        assert len(entries) == 2

    def test_lineage_created_with_id_and_timestamp(self, logger: LineageLogger):
        entry = logger.log(
            action="test",
            entity_type="test",
            entity_id="123",
        )
        assert entry.id is not None
        assert len(entry.id) == 12
        assert entry.timestamp is not None
