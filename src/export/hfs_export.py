"""
HFS Ingestion File Generator.

Builds structured Excel (.xlsx) workbooks with multiple worksheets
formatted to match the "HFS Account Interface (AI)" schema.

Outputs are designed for direct import into HFS Cost Report Software
by CPAs — NOT standalone .ECR files.

Supported worksheets per facility type:
  - Worksheet A: Trial Balance of Expenses (classified)
  - Worksheet A-8: Adjustments (non-allowable costs)
  - Worksheet A-8-1: Statistical Data
  - Worksheet B: Cost Allocation Step-Down
  - Worksheet B-1: RCCCA Ratios
  - HFS AI: Account Interface import format
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import xlsxwriter

from src.config import settings
from src.core.models import (
    ClassificationBatchResult,
    ClassificationResult,
    ExportPayload,
    FacilityType,
)
from src.facilities.registry import get_registry


class HFSExportGenerator:
    """
    Generates HFS-compatible Excel workbooks from classification results.

    The output .xlsx file contains:
    1. Worksheet A — Classified GL mapped to CMS cost centers
    2. Worksheet A-8 — Non-allowable adjustments
    3. Worksheet A-8-1 — Statistical data
    4. Worksheet B — Step-down allocation basis
    5. Worksheet B-1 — CCR computations
    6. HFS AI — Account Interface flat format for direct HFS import
    """

    def __init__(self, facility_type: FacilityType):
        self.facility_type = facility_type
        self.registry = get_registry(facility_type)

    def generate(
        self,
        classification_batch: ClassificationBatchResult,
        output_path: Path | str,
        provider_name: str = "",
        provider_cms_id: str = "",
        fiscal_year_end: str = "",
    ) -> ExportPayload:
        """
        Generate the full HFS-compatible export workbook.

        Args:
            classification_batch: The classified GL data
            output_path: Where to write the .xlsx file
            provider_name: Optional provider name for headers
            provider_cms_id: Optional CMS certification number
            fiscal_year_end: Optional FY end date (e.g., '2026-12-31')

        Returns:
            ExportPayload with all worksheet data
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        workbook = xlsxwriter.Workbook(str(output_path))

        # ── Build data structures ──────────────────────────────────
        ws_a_rows = self._build_worksheet_a(classification_batch)
        ws_a8_rows = self._build_worksheet_a8(classification_batch)
        ws_a81_rows = self._build_worksheet_a81(classification_batch)
        ws_b_rows = self._build_worksheet_b(classification_batch)
        ws_b1_rows = self._build_worksheet_b1(classification_batch)
        hfs_ai_rows = self._build_hfs_ai(classification_batch)

        # ── Write worksheets ───────────────────────────────────────
        self._write_worksheet_a(workbook, ws_a_rows, provider_name, fiscal_year_end)
        self._write_worksheet_a8(workbook, ws_a8_rows, provider_name, fiscal_year_end)
        self._write_worksheet_a81(workbook, ws_a81_rows, provider_name, fiscal_year_end)
        self._write_worksheet_b(workbook, ws_b_rows, provider_name, fiscal_year_end)
        self._write_worksheet_b1(workbook, ws_b1_rows, provider_name, fiscal_year_end)
        self._write_hfs_ai(workbook, hfs_ai_rows, provider_name)

        workbook.close()

        total_amount = sum(abs(r.net_amount) for r in classification_batch.results)
        unallowable_amount = sum(
            abs(r.net_amount) for r in classification_batch.results if r.is_unallowable
        )

        return ExportPayload(
            facility_type=self.facility_type,
            provider_name=provider_name,
            provider_cms_id=provider_cms_id or None,
            fiscal_year_end=fiscal_year_end or None,
            worksheet_a_rows=ws_a_rows,
            worksheet_a8_rows=ws_a8_rows,
            worksheet_a81_rows=ws_a81_rows,
            worksheet_b_rows=ws_b_rows,
            worksheet_b1_rows=ws_b1_rows,
            hfs_ai_rows=hfs_ai_rows,
            classification_batch_id=classification_batch.id,
            total_classified_amount=Decimal(str(total_amount)),
            total_unallowable_amount=Decimal(str(unallowable_amount)),
        )

    # ── Data Builders ──────────────────────────────────────────────

    def _build_worksheet_a(self, batch: ClassificationBatchResult) -> list[dict]:
        """Build Worksheet A rows: classified GL entries by cost center."""
        # Group by cost center
        by_center: dict[str, list[ClassificationResult]] = {}
        for r in batch.results:
            if r.is_unallowable:
                continue
            by_center.setdefault(r.mapped_cost_center_code, []).append(r)

        rows = []
        for code in sorted(by_center.keys()):
            entries = by_center[code]
            total = sum(e.net_amount for e in entries)
            cc = self.registry.get_cost_center(code)
            rows.append({
                "cost_center_code": code,
                "cost_center_name": cc.name if cc else code,
                "line_number": cc.line_number if cc else "",
                "worksheet": cc.worksheet if cc else "A",
                "total_amount": float(total),
                "account_count": len(entries),
                "confidence_min": min(e.confidence_score for e in entries),
                "confidence_max": max(e.confidence_score for e in entries),
            })
        return rows

    def _build_worksheet_a8(self, batch: ClassificationBatchResult) -> list[dict]:
        """Build Worksheet A-8 rows: non-allowable adjustments."""
        rows = []
        for r in batch.results:
            if not r.is_unallowable:
                continue
            rows.append({
                "account_number": r.account_number,
                "account_description": r.account_description,
                "amount": float(r.net_amount),
                "unallowable_category": r.unallowable_category.value if r.unallowable_category else "other",
                "unallowable_reason": r.unallowable_reason or "",
                "worksheet": "A-8",
            })
        return rows

    def _build_worksheet_a81(self, batch: ClassificationBatchResult) -> list[dict]:
        """Build Worksheet A-8-1 rows: statistical data headers."""
        # Statistical data is typically user-provided; this creates the template
        rows = []
        for code in self.registry.general_service_codes:
            cc = self.registry.get_cost_center(code)
            if cc and cc.allocation_method:
                rows.append({
                    "cost_center_code": code,
                    "cost_center_name": cc.name if cc else code,
                    "allocation_method": cc.allocation_method.value,
                    "statistical_value": 0.0,
                    "notes": "User must provide statistical value",
                })
        return rows

    def _build_worksheet_b(self, batch: ClassificationBatchResult) -> list[dict]:
        """Build Worksheet B headers: step-down allocation basis."""
        rows = []
        for code in self.registry.step_down_sequence:
            cc = self.registry.get_cost_center(code)
            if cc:
                rows.append({
                    "cost_center_code": code,
                    "cost_center_name": cc.name,
                    "category": cc.category.value,
                    "allocation_method": cc.allocation_method.value if cc.allocation_method else "accumulated_cost",
                    "step_order": self.registry.step_down_sequence.index(code) + 1,
                })
        return rows

    def _build_worksheet_b1(self, batch: ClassificationBatchResult) -> list[dict]:
        """Build Worksheet B-1 rows: CCR computation headers."""
        rows = []
        for r in batch.results:
            if r.is_unallowable:
                continue
            cc = self.registry.get_cost_center(r.mapped_cost_center_code)
            if cc and cc.category.value == "revenue_producing":
                rows.append({
                    "cost_center_code": r.mapped_cost_center_code,
                    "cost_center_name": cc.name,
                    "total_cost": float(abs(r.net_amount)),
                    "total_charges": 0.0,  # User provides
                    "ccr": 0.0,             # Computed: cost / charges
                    "ccr_range_min": cc.ccr_range_min,
                    "ccr_range_max": cc.ccr_range_max,
                    "ccr_in_range": None,
                })
        return rows

    def _build_hfs_ai(self, batch: ClassificationBatchResult) -> list[dict]:
        """
        Build HFS Account Interface format — flat table for direct import.

        HFS AI format columns:
          ACCT_NO, ACCT_NAME, AMOUNT, CC_CODE, CC_NAME, WORKSHEET, PERIOD
        """
        rows = []
        for r in batch.results:
            rows.append({
                "ACCT_NO": r.account_number,
                "ACCT_NAME": r.account_description,
                "AMOUNT": float(r.net_amount),
                "CC_CODE": r.mapped_cost_center_code,
                "CC_NAME": r.mapped_cost_center_name,
                "WORKSHEET": r.mapped_worksheet,
                "CONFIDENCE": r.confidence_score,
                "IS_UNALLOWABLE": "Y" if r.is_unallowable else "N",
            })
        return rows

    # ── Worksheet Writers ──────────────────────────────────────────

    def _write_worksheet_a(
        self, workbook: Any, rows: list[dict], provider: str, fye: str
    ) -> None:
        """Write Worksheet A — Trial Balance of Expenses."""
        ws = workbook.add_worksheet("Worksheet A")
        formats = self._create_formats(workbook)

        # Header
        ws.merge_range(0, 0, 0, 4, f"Worksheet A — Trial Balance of Expenses", formats["title"])
        ws.merge_range(1, 0, 1, 4, f"Provider: {provider}  |  FY End: {fye}", formats["subtitle"])
        ws.set_row(0, 30)

        # Column headers
        headers = ["Cost Center Code", "Cost Center Name", "Line #", "Total Amount", "Account Count"]
        for col, h in enumerate(headers):
            ws.write(3, col, h, formats["header"])
        ws.set_column(0, 0, 18)
        ws.set_column(1, 1, 40)
        ws.set_column(2, 2, 8)
        ws.set_column(3, 3, 18)
        ws.set_column(4, 4, 14)

        # Data
        for i, row in enumerate(rows):
            r = i + 4
            ws.write(r, 0, row["cost_center_code"], formats["normal"])
            ws.write(r, 1, row["cost_center_name"], formats["normal"])
            ws.write(r, 2, row["line_number"] or "", formats["normal"])
            ws.write_number(r, 3, row["total_amount"], formats["money"])
            ws.write_number(r, 4, row["account_count"], formats["normal"])

    def _write_worksheet_a8(
        self, workbook: Any, rows: list[dict], provider: str, fye: str
    ) -> None:
        """Write Worksheet A-8 — Non-Allowable Adjustments."""
        ws = workbook.add_worksheet("Worksheet A-8")
        formats = self._create_formats(workbook)

        ws.merge_range(0, 0, 0, 4, "Worksheet A-8 — Non-Allowable Adjustments", formats["title"])
        ws.merge_range(1, 0, 1, 4, f"Provider: {provider}  |  FY End: {fye}", formats["subtitle"])

        headers = ["Account #", "Description", "Amount", "Category", "Reason"]
        for col, h in enumerate(headers):
            ws.write(3, col, h, formats["header"])
        ws.set_column(0, 0, 14)
        ws.set_column(1, 1, 45)
        ws.set_column(2, 2, 18)
        ws.set_column(3, 3, 18)
        ws.set_column(4, 4, 50)

        for i, row in enumerate(rows):
            r = i + 4
            ws.write(r, 0, row["account_number"], formats["normal"])
            ws.write(r, 1, row["account_description"], formats["normal"])
            ws.write_number(r, 2, row["amount"], formats["money"])
            ws.write(r, 3, row["unallowable_category"], formats["normal"])
            ws.write(r, 4, row["unallowable_reason"], formats["normal"])

    def _write_worksheet_a81(
        self, workbook: Any, rows: list[dict], provider: str, fye: str
    ) -> None:
        """Write Worksheet A-8-1 — Statistical Data."""
        ws = workbook.add_worksheet("Worksheet A-8-1")
        formats = self._create_formats(workbook)

        ws.merge_range(0, 0, 0, 3, "Worksheet A-8-1 — Statistical Data", formats["title"])
        ws.merge_range(1, 0, 1, 3, f"Provider: {provider}  |  FY End: {fye}", formats["subtitle"])

        headers = ["Cost Center", "Name", "Allocation Method", "Statistical Value"]
        for col, h in enumerate(headers):
            ws.write(3, col, h, formats["header"])
        ws.set_column(0, 0, 14)
        ws.set_column(1, 1, 40)
        ws.set_column(2, 2, 22)
        ws.set_column(3, 3, 18)

        for i, row in enumerate(rows):
            r = i + 4
            ws.write(r, 0, row["cost_center_code"], formats["normal"])
            ws.write(r, 1, row["cost_center_name"], formats["normal"])
            ws.write(r, 2, row["allocation_method"], formats["normal"])
            ws.write(r, 3, row.get("statistical_value", 0.0), formats["normal"])

    def _write_worksheet_b(
        self, workbook: Any, rows: list[dict], provider: str, fye: str
    ) -> None:
        """Write Worksheet B — Step-Down Allocation Basis."""
        ws = workbook.add_worksheet("Worksheet B")
        formats = self._create_formats(workbook)

        ws.merge_range(0, 0, 0, 4, "Worksheet B — Step-Down Allocation Sequence", formats["title"])
        ws.merge_range(1, 0, 1, 4, f"Provider: {provider}  |  FY End: {fye}", formats["subtitle"])

        headers = ["Step", "Cost Center", "Name", "Category", "Allocation Method"]
        for col, h in enumerate(headers):
            ws.write(3, col, h, formats["header"])
        ws.set_column(0, 0, 6)
        ws.set_column(1, 1, 14)
        ws.set_column(2, 2, 40)
        ws.set_column(3, 3, 20)
        ws.set_column(4, 4, 24)

        for i, row in enumerate(rows):
            r = i + 4
            ws.write(r, 0, row["step_order"], formats["normal"])
            ws.write(r, 1, row["cost_center_code"], formats["normal"])
            ws.write(r, 2, row["cost_center_name"], formats["normal"])
            ws.write(r, 3, row["category"], formats["normal"])
            ws.write(r, 4, row["allocation_method"], formats["normal"])

    def _write_worksheet_b1(
        self, workbook: Any, rows: list[dict], provider: str, fye: str
    ) -> None:
        """Write Worksheet B-1 — RCCCA Ratios."""
        ws = workbook.add_worksheet("Worksheet B-1")
        formats = self._create_formats(workbook)

        ws.merge_range(0, 0, 0, 5, "Worksheet B-1 — RCCCA Ratios", formats["title"])
        ws.merge_range(1, 0, 1, 5, f"Provider: {provider}  |  FY End: {fye}", formats["subtitle"])

        headers = [
            "Cost Center", "Name", "Total Cost", "Total Charges",
            "CCR", "Expected Range",
        ]
        for col, h in enumerate(headers):
            ws.write(3, col, h, formats["header"])

        ws.set_column(0, 0, 14)
        ws.set_column(1, 1, 40)
        ws.set_column(2, 2, 18)
        ws.set_column(3, 3, 18)
        ws.set_column(4, 4, 12)
        ws.set_column(5, 5, 24)

        for i, row in enumerate(rows):
            r = i + 4
            ws.write(r, 0, row["cost_center_code"], formats["normal"])
            ws.write(r, 1, row["cost_center_name"], formats["normal"])
            ws.write_number(r, 2, row["total_cost"], formats["money"])
            ws.write_number(r, 3, 0.0, formats["money"])  # User provides charges
            ws.write(r, 4, "", formats["normal"])  # Computed later
            ccr_range = ""
            if row.get("ccr_range_min") and row.get("ccr_range_max"):
                ccr_range = f"{row['ccr_range_min']:.2f} - {row['ccr_range_max']:.2f}"
            ws.write(r, 5, ccr_range, formats["normal"])

    def _write_hfs_ai(
        self, workbook: Any, rows: list[dict], provider: str
    ) -> None:
        """Write HFS Account Interface sheet — flat import format."""
        ws = workbook.add_worksheet("HFS AI")
        formats = self._create_formats(workbook)

        ws.merge_range(0, 0, 0, 7, "HFS Account Interface — Direct Import Format", formats["title"])
        ws.merge_range(1, 0, 1, 7, f"Provider: {provider}", formats["subtitle"])

        headers = [
            "ACCT_NO", "ACCT_NAME", "AMOUNT", "CC_CODE",
            "CC_NAME", "WORKSHEET", "CONFIDENCE", "UNALLOWABLE",
        ]
        for col, h in enumerate(headers):
            ws.write(3, col, h, formats["header"])

        ws.set_column(0, 0, 14)
        ws.set_column(1, 1, 50)
        ws.set_column(2, 2, 18)
        ws.set_column(3, 3, 10)
        ws.set_column(4, 4, 35)
        ws.set_column(5, 5, 10)
        ws.set_column(6, 6, 12)
        ws.set_column(7, 7, 12)

        for i, row in enumerate(rows):
            r = i + 4
            ws.write(r, 0, row["ACCT_NO"], formats["normal"])
            ws.write(r, 1, row["ACCT_NAME"], formats["normal"])
            ws.write_number(r, 2, row["AMOUNT"], formats["money"])
            ws.write(r, 3, row["CC_CODE"], formats["normal"])
            ws.write(r, 4, row["CC_NAME"], formats["normal"])
            ws.write(r, 5, row["WORKSHEET"], formats["normal"])
            ws.write_number(r, 6, row["CONFIDENCE"], formats["pct"])
            ws.write(r, 7, row["IS_UNALLOWABLE"], formats["normal"])

    def _create_formats(self, workbook: Any) -> dict:
        """Create and return a dict of reusable XlsxWriter formats."""
        return {
            "title": workbook.add_format({
                "bold": True, "font_size": 14, "font_color": "#1a1a2e",
            }),
            "subtitle": workbook.add_format({
                "italic": True, "font_size": 10, "font_color": "#666666",
            }),
            "header": workbook.add_format({
                "bold": True, "font_size": 10, "bg_color": "#1a1a2e",
                "font_color": "white", "border": 1, "text_wrap": True,
            }),
            "normal": workbook.add_format({
                "font_size": 10, "border": 1,
            }),
            "money": workbook.add_format({
                "font_size": 10, "num_format": "#,##0.00", "border": 1,
            }),
            "pct": workbook.add_format({
                "font_size": 10, "num_format": "0.00%", "border": 1,
            }),
        }
