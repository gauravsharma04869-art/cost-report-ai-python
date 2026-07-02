"""
Tests for core data models — validation, sanitization, and type safety.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.models import (
    ClassificationResult,
    ConfidenceLevel,
    CostCenterDefinition,
    CostCenterCategory,
    FacilityType,
    GrossGLTransaction,
    ParsedIngestionResult,
    ProcessingSession,
)


class TestGrossGLTransaction:
    def test_minimal_transaction(self):
        """A transaction requires only account_number and description."""
        txn = GrossGLTransaction(
            account_number="6010",
            account_description="RN Salaries",
        )
        assert txn.account_number == "6010"
        assert txn.account_description == "RN Salaries"
        assert txn.debit_amount == Decimal("0.00")
        assert txn.credit_amount == Decimal("0.00")
        assert txn.net_amount == Decimal("0.00")
        assert txn.absolute_amount == Decimal("0.00")

    def test_net_amount(self):
        txn = GrossGLTransaction(
            account_number="6010",
            account_description="Test",
            debit_amount=Decimal("1000.00"),
            credit_amount=Decimal("200.00"),
        )
        assert txn.net_amount == Decimal("800.00")

    def test_currency_sanitization(self):
        txn = GrossGLTransaction(
            account_number="6010",
            account_description="Test",
            debit_amount="$1,234.56",
            credit_amount="($500.00)",
        )
        assert txn.debit_amount == Decimal("1234.56")
        assert txn.credit_amount == Decimal("-500.00")
        assert txn.net_amount == Decimal("1734.56")

    def test_empty_string_amount(self):
        txn = GrossGLTransaction(
            account_number="6010",
            account_description="Test",
            debit_amount="",
            credit_amount="-",
        )
        assert txn.debit_amount == Decimal("0.00")
        assert txn.credit_amount == Decimal("0.00")


class TestClassificationResult:
    def test_confidence_level_derivation(self):
        r = ClassificationResult(
            transaction_id="abc",
            account_number="6010",
            account_description="RN Salaries",
            net_amount=Decimal("1000"),
            mapped_cost_center_code="20",
            mapped_cost_center_name="Routine Care",
            confidence_score=0.95,
            confidence_level=None,  # Should auto-derive
        )
        assert r.confidence_level == ConfidenceLevel.HIGH

    def test_low_confidence(self):
        r = ClassificationResult(
            transaction_id="abc",
            account_number="9999",
            account_description="Misc",
            net_amount=Decimal("100"),
            mapped_cost_center_code="04",
            mapped_cost_center_name="A&G",
            confidence_score=0.45,
        )
        assert r.confidence_level == ConfidenceLevel.LOW

    def test_medium_confidence(self):
        r = ClassificationResult(
            transaction_id="abc",
            account_number="7000",
            account_description="Office Supplies",
            net_amount=Decimal("500"),
            mapped_cost_center_code="04",
            mapped_cost_center_name="A&G",
            confidence_score=0.75,
        )
        assert r.confidence_level == ConfidenceLevel.MEDIUM


class TestCostCenterDefinition:
    def test_minimal(self):
        cc = CostCenterDefinition(
            code="04",
            name="Administrative & General",
            category=CostCenterCategory.GENERAL_SERVICE,
        )
        assert cc.code == "04"
        assert cc.allowable is True
        assert cc.worksheet == "A"

    def test_non_allowable(self):
        cc = CostCenterDefinition(
            code="90",
            name="Marketing",
            category=CostCenterCategory.NON_ALLOWABLE,
            allowable=False,
        )
        assert cc.allowable is False


class TestProcessingSession:
    def test_session_creation(self):
        session = ProcessingSession(
            facility_type=FacilityType.HOSPITAL,
            provider_name="St. Mary's Hospital",
        )
        assert session.status == "created"
        assert session.facility_type == FacilityType.HOSPITAL
        assert len(session.id) == 12


class TestParsedIngestionResult:
    def test_empty_result(self):
        result = ParsedIngestionResult(
            source_file="test.csv",
            entry_type="trial_balance",
        )
        assert result.row_count == 0
        assert result.error_count == 0

    def test_with_entries(self):
        entries = [
            GrossGLTransaction(account_number="6010", account_description="Salaries"),
            GrossGLTransaction(account_number="7010", account_description="Supplies"),
        ]
        result = ParsedIngestionResult(
            source_file="test.csv",
            entry_type="trial_balance",
            entries=entries,
        )
        assert result.row_count == 2
