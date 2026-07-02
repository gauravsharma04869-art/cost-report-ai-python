"""
Tests for all document parsers — trial balance, census, payroll, PS&R.
"""

import csv
from decimal import Decimal
import io
from pathlib import Path

import pytest

from src.core.models import EntryType
from src.ingestors.base_parser import detect_column_mapping, sanitize_amount
from src.ingestors.trial_balance_parser import TrialBalanceParser


class TestSanitization:
    def test_sanitize_amount_basic(self):
        assert sanitize_amount("$1,234.56") == Decimal("1234.56")
        assert sanitize_amount("($500.00)") == Decimal("-500.00")
        assert sanitize_amount("1,000") == Decimal("1000")
        assert sanitize_amount("") == Decimal("0")
        assert sanitize_amount("-$50.00") == Decimal("-50.00")

    def test_sanitize_amount_numeric(self):
        assert sanitize_amount(1000) == Decimal("1000")
        assert sanitize_amount(99.99) == Decimal("99.99")


class TestColumnDetection:
    def test_standard_headers(self):
        headers = ["Account #", "Description", "Debit", "Credit"]
        mapping = detect_column_mapping(headers)
        assert mapping["account_number"] == "Account #"
        assert mapping["account_description"] == "Description"
        assert mapping["debit_amount"] == "Debit"
        assert mapping["credit_amount"] == "Credit"

    def test_variant_names(self):
        headers = ["GL Account", "Account Name", "DR", "CR", "Period"]
        mapping = detect_column_mapping(headers)
        assert "account_number" in mapping
        assert "account_description" in mapping
        assert "debit_amount" in mapping
        assert "credit_amount" in mapping
        assert "period" in mapping

    def test_unknown_headers(self):
        headers = ["Foo", "Bar", "Baz"]
        mapping = detect_column_mapping(headers)
        # Should return only matched headers
        assert isinstance(mapping, dict)


class TestTrialBalanceParser:
    def setup_method(self):
        self.parser = TrialBalanceParser()

    def _make_csv(self, rows: list[list[str]]) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(rows)
        return output.getvalue().encode("utf-8")

    def test_parse_csv(self):
        """Parse a simple CSV trial balance."""
        csv_content = self._make_csv([
            ["Account #", "Description", "Debit", "Credit"],
            ["6010", "RN Salaries - Med Surg", "100000.00", "0"],
            ["7010", "Lab Supplies", "25000.00", "0"],
            ["8010", "Office Rent", "12000.00", "0"],
        ])

        result = self.parser.parse(csv_content, source_file="test.csv")
        assert result.row_count == 3
        assert result.error_count == 0
        assert result.entry_type == EntryType.TRIAL_BALANCE

        entries = result.entries
        assert entries[0].account_number == "6010"
        assert entries[0].account_description == "RN Salaries - Med Surg"
        assert entries[0].debit_amount == 100000
        assert entries[1].account_number == "7010"

    def test_parse_with_credit_amounts(self):
        csv_content = self._make_csv([
            ["Account #", "Description", "Debit", "Credit"],
            ["2100", "AP - Trade", "0", "50000.00"],
            ["3100", "Equity", "0", "200000.00"],
        ])

        result = self.parser.parse(csv_content, source_file="test.csv")
        assert result.row_count == 2
        assert result.entries[0].credit_amount == 50000
        assert result.entries[0].net_amount == -50000  # Debit 0 - Credit 50000 = -50000

    def test_parse_with_currency_symbols(self):
        csv_content = self._make_csv([
            ["Account #", "Description", "Debit", "Credit"],
            ["6010", "Salaries", "$100,000.00", "$0.00"],
        ])

        result = self.parser.parse(csv_content, source_file="test.csv")
        assert result.entries[0].debit_amount == 100000

    def test_parse_empty_file(self):
        csv_content = self._make_csv([])
        result = self.parser.parse(csv_content, source_file="empty.csv")
        assert result.row_count == 0

    def test_column_mapping_detected(self):
        csv_content = self._make_csv([
            ["GL Account", "Account Name", "DR", "CR", "Period", "Dept"],
            ["6010", "Salaries", "1000", "0", "2026-06", "DEPT01"],
        ])
        result = self.parser.parse(csv_content, source_file="test.csv")
        assert "account_number" in result.column_mapping
        assert "period" in result.column_mapping
        assert result.entries[0].period == "2026-06"
        assert result.entries[0].department_code == "DEPT01"
