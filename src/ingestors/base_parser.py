"""
Base parser with common utilities for all document types.
"""

from __future__ import annotations

import csv
import io
import re
import time
from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from src.core.models import EntryType, GrossGLTransaction, ParsedIngestionResult


def sanitize_amount(value: Any) -> Decimal:
    """
    Sanitize a raw string/cell value into a proper Decimal.

    Handles:
    - Currency symbols ($, €, etc.)
    - Commas as thousand separators
    - Parentheses for negative amounts
    - Leading/trailing whitespace
    - Empty strings and non-numeric values
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if not isinstance(value, str):
        return Decimal("0.00")

    v = value.strip()
    if not v or v == "-":
        return Decimal("0.00")

    # Handle parenthetical negatives: ($1,234.56) → -1234.56
    neg = False
    if v.startswith("(") and v.endswith(")"):
        neg = True
        v = v[1:-1]

    # Remove currency symbols, commas, and spaces
    v = re.sub(r'[\$,€£¥\s]', "", v)

    if neg:
        v = f"-{v}"

    try:
        return Decimal(v)
    except Exception:
        return Decimal("0.00")


def detect_column_mapping(headers: list[str]) -> dict[str, str]:
    """
    Auto-detect column mapping from header names.

    Returns a mapping like {'account_number': 'Acct#', 'description': 'Account Name', ...}
    """
    header_lower = [h.strip().lower() for h in headers]

    mapping: dict[str, Optional[str]] = {
        "account_number": None,
        "account_description": None,
        "debit_amount": None,
        "credit_amount": None,
        "period": None,
        "department_code": None,
        "department_name": None,
    }

    keywords = {
        "account_number": ["account", "acct", "acct #", "acct#", "account #", "account#", "account no", "gl account", "gl no", "code", "account code"],
        "account_description": ["description", "desc", "account name", "name", "account description", "gl description", "particulars", "narrative"],
        "debit_amount": ["debit", "dr", "debit amount", "debit amt", "charge"],
        "credit_amount": ["credit", "cr", "credit amount", "credit amt"],
        "period": ["period", "month", "fiscal period", "fiscal month", "period end", "accounting period"],
        "department_code": ["department", "dept", "dept code", "dept #", "dept#", "cost center", "cc", "department code"],
        "department_name": ["department name", "dept name", "dept description", "department description"],
    }

    for i, h in enumerate(header_lower):
        h_clean = h.strip().rstrip(".")
        for field, terms in keywords.items():
            if mapping[field] is not None:
                continue
            # Exact or leading match
            if h_clean in terms or any(t in h_clean for t in terms if len(t) > 3):
                mapping[field] = headers[i]

    return {k: v for k, v in mapping.items() if v is not None}


def sanitize_string(value: Any) -> str:
    """Clean and normalize a string value."""
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    return value.strip().replace("\n", " ").replace("\r", "")


class BaseParser(ABC):
    """Abstract base for all document parsers."""

    entry_type: EntryType

    @abstractmethod
    def parse(self, content: bytes, source_file: str, **kwargs) -> ParsedIngestionResult:
        """Parse raw file content into structured GL entries."""
        ...

    def parse_file(self, path: str | Path, **kwargs) -> ParsedIngestionResult:
        """Convenience: parse a file from disk."""
        path = Path(path)
        content = path.read_bytes()
        return self.parse(content, path.name, **kwargs)
