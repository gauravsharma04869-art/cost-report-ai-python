"""
Pipeline Orchestrator — ties together ingestion → classification → export.

Manages the full lifecycle of a processing session, including:
  1. File parsing (multi-modal)
  2. AI classification
  3. HFS export generation
  4. Audit trail logging
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from src.config import settings
from src.core.lineage import LineageLogger
from src.core.models import (
    ClassificationBatchResult,
    ExportPayload,
    FacilityType,
    ParsedIngestionResult,
    ProcessingSession,
)
from src.export.hfs_export import HFSExportGenerator
from src.facilities.registry import get_registry
from src.ingestors.census_parser import CensusParser
from src.ingestors.payroll_parser import PayrollParser
from src.ingestors.psr_parser import PSRSummaryParser
from src.ingestors.trial_balance_parser import TrialBalanceParser
from src.llm.classifier import GLClassifier


class Pipeline:
    """
    End-to-end pipeline orchestrator.

    Usage:
        pipeline = Pipeline(facility_type=FacilityType.HOSPITAL)
        result = pipeline.run_full("data/samples/hospital_gl.csv")
        # result contains ingestion + classification + export data
    """

    def __init__(
        self,
        facility_type: FacilityType,
        provider_name: str = "",
        provider_cms_id: str = "",
        fiscal_year_end: str = "",
        llm_model: Optional[str] = None,
    ):
        self.facility_type = facility_type
        self.provider_name = provider_name
        self.provider_cms_id = provider_cms_id
        self.fiscal_year_end = fiscal_year_end
        self.classifier = GLClassifier(model=llm_model) if llm_model else GLClassifier()
        self.lineage = LineageLogger()
        self.session = ProcessingSession(facility_type=facility_type, provider_name=provider_name)

        # Parser registry
        self.parsers = {
            "trial_balance": TrialBalanceParser(),
            "census": CensusParser(),
            "payroll": PayrollParser(),
            "psr": PSRSummaryParser(),
        }

    def parse_file(self, file_path: str | Path, file_type: Optional[str] = None) -> ParsedIngestionResult:
        """
        Parse a single file. Auto-detects file type if not specified.

        Args:
            file_path: Path to the source file
            file_type: One of 'trial_balance', 'census', 'payroll', 'psr', or None for auto-detect

        Returns:
            ParsedIngestionResult with structured GL entries
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        content = path.read_bytes()
        ext = path.suffix.lower()

        # Auto-detect parser from file type or extension hints
        parser_key = file_type or self._detect_parser(path.name, ext)
        parser = self.parsers.get(parser_key)
        if parser is None:
            raise ValueError(f"Unknown file type: {parser_key}. Use: trial_balance, census, payroll, psr")

        result = parser.parse(content, path.name)

        # Log to lineage
        self.lineage.log_import(
            source_file=path.name,
            row_count=result.row_count,
            error_count=result.error_count,
            ingestion_id=result.id,
        )

        self.session.ingestion_results.append(result.id)
        self.session.status = "importing"

        return result

    def classify(
        self,
        ingestion_result: ParsedIngestionResult,
        batch_size: int = 10,
    ) -> ClassificationBatchResult:
        """
        Run AI classification on a parsed ingestion result.

        Args:
            ingestion_result: Result from parse_file()
            batch_size: Number of accounts per LLM call

        Returns:
            ClassificationBatchResult
        """
        if not ingestion_result.entries:
            raise ValueError("No entries to classify. Run parse_file() first.")

        self.session.status = "classifying"
        batch_result = self.classifier.classify_batch(
            transactions=ingestion_result.entries,
            facility_type=self.facility_type,
            batch_size=batch_size,
        )
        batch_result.ingestion_id = ingestion_result.id

        # Log classifications to lineage
        for r in batch_result.results:
            self.lineage.log_classification(
                transaction_id=r.transaction_id,
                account_number=r.account_number,
                from_center=None,
                to_center=r.mapped_cost_center_code,
                confidence=r.confidence_score,
                actor="ai",
                reason=r.reasoning,
            )

        self.session.classification_batch_id = batch_result.id
        return batch_result

    def export(
        self,
        classification_batch: ClassificationBatchResult,
        output_path: Optional[str | Path] = None,
    ) -> ExportPayload:
        """
        Generate HFS-compatible export file.

        Args:
            classification_batch: Result from classify()
            output_path: Where to write the .xlsx file

        Returns:
            ExportPayload with all worksheet data
        """
        if output_path is None:
            output_path = settings.OUTPUT_DIR / f"export_{self.facility_type.value}_{classification_batch.id[:8]}.xlsx"

        self.session.status = "exporting"
        generator = HFSExportGenerator(facility_type=self.facility_type)
        payload = generator.generate(
            classification_batch=classification_batch,
            output_path=output_path,
            provider_name=self.provider_name,
            provider_cms_id=self.provider_cms_id,
            fiscal_year_end=self.fiscal_year_end,
        )

        # Log export to lineage
        self.lineage.log_export(
            export_id=payload.id,
            format="xlsx",
            facility_type=self.facility_type.value,
            row_count=len(payload.hfs_ai_rows),
        )

        self.session.export_payload_id = payload.id
        self.session.status = "completed"
        return payload

    def run_full(
        self,
        file_path: str | Path,
        output_path: Optional[str | Path] = None,
        file_type: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Run the full pipeline on a single file.

        Args:
            file_path: Path to the source file
            output_path: Where to write the export file
            file_type: Optional parser type override

        Returns:
            Dict with 'ingestion', 'classification', 'export' keys
        """
        ingestion = self.parse_file(file_path, file_type=file_type)
        classification = self.classify(ingestion)
        export = self.export(classification, output_path=output_path)

        return {
            "session_id": self.session.id,
            "ingestion": ingestion.model_dump(mode="json"),
            "classification": classification.model_dump(mode="json"),
            "export": export.model_dump(mode="json"),
        }

    @staticmethod
    def _detect_parser(filename: str, ext: str) -> str:
        """Auto-detect the parser type from filename and extension."""
        name_lower = filename.lower()

        if any(kw in name_lower for kw in ["census", "patient day", "visit"]):
            return "census"
        if any(kw in name_lower for kw in ["payroll", "salary", "wage", "labor"]):
            return "payroll"
        if any(kw in name_lower for kw in ["psr", "ps&r", "provider statistical", "reimbursement"]):
            return "psr"
        if ext in (".xlsx", ".xls", ".csv", ".tsv", ".txt"):
            return "trial_balance"

        return "trial_balance"
