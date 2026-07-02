"""
Pydantic domain models for the Cost Report AI pipeline.

Covers the full data lifecycle:
  RawIngestion → ParsedEntry → ClassifiedEntry → AllocatedCost → ExportPayload
                                                                             
Each stage adds provenance metadata for full audit trail transparency.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class FacilityType(str, Enum):
    """CMS cost report form types supported by the platform."""

    HOSPITAL = "hospital"              # CMS-2552-10
    SNF = "snf"                        # CMS-2540-10
    HOSPICE = "hospice"                # CMS-1984-14
    HHA = "hha"                        # CMS-1728-20


class CostCenterCategory(str, Enum):
    """Classification of cost centers per CMS methodology."""

    GENERAL_SERVICE = "general_service"       # Cost centers 01-16 (overhead)
    REVENUE_PRODUCING = "revenue_producing"    # Cost centers 20+ (direct patient care)
    NON_ALLOWABLE = "non_allowable"            # Must be excluded from Medicare payment
    RECLASSIFICATION = "reclassification"      # Worksheet A-6 reclasses


class ConfidenceLevel(str, Enum):
    """Three-state confidence system for AI classifications."""

    HIGH = "high"        # >= 90% — auto-classified, shown in green
    MEDIUM = "medium"    # 70-89% — flagged for review, shown in amber
    LOW = "low"          # < 70% — requires human input, shown in red


class AllocationMethod(str, Enum):
    """CMS-permitted cost allocation bases for step-down."""

    ACCUMULATED_COST = "accumulated_cost"
    SALARIES = "salaries"
    NURSING_SALARIES = "nursing_salaries"
    SQUARE_FEET = "square_feet"
    MEALS_SERVED = "meals_served"
    POUNDS_LAUNDRY = "pounds_laundry"
    PATIENT_DAYS = "patient_days"
    EQUAL_DISTRIBUTION = "equal_distribution"
    DIRECT_ASSIGNMENT = "direct_assignment"
    STATISTICAL = "statistical"  # User-provided statistical basis


class UnallowableCategory(str, Enum):
    """Categories of non-allowable costs per Medicare guidelines."""

    MARKETING = "marketing"
    LOBBYING = "lobbying"
    ENTERTAINMENT = "entertainment"
    CHARITY = "charity"
    POLITICAL = "political"
    FINES = "fines"
    DONATIONS = "donations"
    OTHER = "other"


class EntryType(str, Enum):
    """Source document types that feed into the pipeline."""

    TRIAL_BALANCE = "trial_balance"
    CENSUS_REPORT = "census_report"
    PAYROLL_REGISTER = "payroll_register"
    PSR_SUMMARY = "psr_summary"


class AdjustmentType(str, Enum):
    """Types of adjustments on Worksheet A-8 / A-8-1."""

    UNALLOWABLE = "unallowable"
    CAPITAL_RELATED = "capital_related"
    RELATED_ORGANIZATION = "related_organization"
    DONATION = "donation"
    GRANT_EXPENSE = "grant_expense"
    OTHER = "other"


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class CostCenterDefinition(BaseModel):
    """A single CMS-defined cost center line item on a worksheet."""

    code: str = Field(..., description="CMS cost center code (e.g., '01', '20')")
    name: str = Field(..., description="CMS cost center name (e.g., 'Capital Related - Buildings & Fixtures')")
    worksheet: str = Field(default="A", description="Worksheet designation (A, A-6, A-8, B, etc.)")
    category: CostCenterCategory = Field(default=..., description="Cost center category")
    line_number: Optional[int] = Field(default=None, description="Worksheet line number")
    description: str = Field(default="", description="Detailed description of what this cost center covers")
    allowable: bool = Field(default=True, description="Whether costs in this center are Medicare-allowable")
    ccr_range_min: Optional[float] = Field(default=None, description="Expected minimum CCR for smell test")
    ccr_range_max: Optional[float] = Field(default=None, description="Expected maximum CCR for smell test")
    allocation_method: Optional[AllocationMethod] = Field(default=None, description="Default step-down allocation method")
    parent_code: Optional[str] = Field(default=None, description="Parent cost center code if this is a sub-center")


class GrossGLTransaction(BaseModel):
    """A raw, unprocessed general ledger transaction from a trial balance."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    account_number: str = Field(..., description="GL account number from the trial balance")
    account_description: str = Field(..., description="GL account name/description from the trial balance")
    debit_amount: Decimal = Field(default=Decimal("0.00"), description="Debit amount (positive)")
    credit_amount: Decimal = Field(default=Decimal("0.00"), description="Credit amount (positive)")
    period: Optional[str] = Field(default=None, description="Fiscal period (e.g., '2026-06')")
    department_code: Optional[str] = Field(default=None, description="Originating department code if available")
    department_name: Optional[str] = Field(default=None, description="Originating department name if available")
    source_file: Optional[str] = Field(default=None, description="Name of the source file")
    row_index: Optional[int] = Field(default=None, description="Row number in the source file")

    @field_validator("debit_amount", "credit_amount", mode="before")
    @classmethod
    def parse_decimal(cls, v: Any) -> Decimal:
        if isinstance(v, str):
            v = v.replace("$", "").replace(",", "").replace("(", "-").replace(")", "").strip()
            if v == "" or v == "-":
                return Decimal("0.00")
            return Decimal(v)
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return Decimal(v)

    @property
    def net_amount(self) -> Decimal:
        """Standard accounting: net = debit - credit."""
        return self.debit_amount - self.credit_amount

    @property
    def absolute_amount(self) -> Decimal:
        """Absolute value of the net amount for classification purposes."""
        return abs(self.net_amount)


class ParsedIngestionResult(BaseModel):
    """Result of parsing a single source file into structured GL entries."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_file: str = Field(..., description="Original filename")
    entry_type: EntryType = Field(..., description="Type of source document")
    facility_type: Optional[FacilityType] = Field(default=None, description="Identified or assigned facility type")
    entries: list[GrossGLTransaction] = Field(default_factory=list, description="Parsed GL transactions")
    row_count: int = Field(default=0, description="Total rows parsed")
    error_count: int = Field(default=0, description="Rows that failed to parse")
    errors: list[dict] = Field(default_factory=list, description="Row-level parsing errors with context")
    column_mapping: dict[str, str] = Field(default_factory=dict, description="Auto-detected column mapping")
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: float = Field(default=0.0, description="Milliseconds to parse")

    def model_post_init(self, __context: Any) -> None:
        """Auto-sync row_count from entries if entries exist and row_count is 0."""
        if self.entries and self.row_count == 0:
            object.__setattr__(self, "row_count", len(self.entries))


class ClassificationResult(BaseModel):
    """Output of the AI classification engine: a single GL entry mapped to a CMS line item."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    transaction_id: str = Field(..., description="Reference to the source GL transaction ID")
    account_number: str = Field(..., description="GL account number")
    account_description: str = Field(..., description="Original GL account description")
    net_amount: Decimal = Field(..., description="Net amount carried forward")

    # CMS mapping
    mapped_cost_center_code: str = Field(..., description="CMS cost center code assigned by AI")
    mapped_cost_center_name: str = Field(..., description="CMS cost center name assigned by AI")
    mapped_worksheet: str = Field(default="A", description="Target worksheet")

    # Confidence
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI confidence score (0-1)")
    confidence_level: Optional[ConfidenceLevel] = Field(default=None, description="Calibrated confidence level — auto-derived from score if not explicitly set")

    # Audit trail
    reasoning: str = Field(default="", description="AI's reasoning for this classification")
    source_attribution: str = Field(default="", description="What the AI based its decision on")
    is_unallowable: bool = Field(default=False, description="Flagged as Medicare non-allowable")
    unallowable_category: Optional[UnallowableCategory] = Field(default=None)
    unallowable_reason: Optional[str] = Field(default=None)
    is_human_override: bool = Field(default=False)
    human_override_reason: Optional[str] = Field(default=None)
    classified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_used: str = Field(default="", description="LLM model ID used for classification")

    @model_validator(mode="after")
    def _derive_confidence_level(self) -> "ClassificationResult":
        if self.confidence_level is None:
            if self.confidence_score >= 0.90:
                self.confidence_level = ConfidenceLevel.HIGH
            elif self.confidence_score >= 0.70:
                self.confidence_level = ConfidenceLevel.MEDIUM
            else:
                self.confidence_level = ConfidenceLevel.LOW
        return self


class ClassificationBatchResult(BaseModel):
    """Complete batch result from running classification on a parsed ingestion."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    ingestion_id: str = Field(..., description="Reference to the source ParsedIngestionResult")
    facility_type: FacilityType = Field(..., description="Facility type used for classification")
    results: list[ClassificationResult] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    processing_time_ms: float = Field(default=0.0)
    model_used: str = Field(default="")


class ExportPayload(BaseModel):
    """HFS-compatible export payload — a complete data set ready for import into HFS Software."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    facility_type: FacilityType
    provider_name: str = Field(default="")
    provider_cms_id: Optional[str] = Field(default=None)
    fiscal_year_end: Optional[str] = Field(default=None)

    # Worksheet data — each is a list of dicts for tabular export
    worksheet_a_rows: list[dict] = Field(default_factory=list)
    worksheet_a8_rows: list[dict] = Field(default_factory=list)
    worksheet_a81_rows: list[dict] = Field(default_factory=list)
    worksheet_b_rows: list[dict] = Field(default_factory=list)
    worksheet_b1_rows: list[dict] = Field(default_factory=list)

    # HFS Account Interface format
    hfs_ai_rows: list[dict] = Field(default_factory=list)

    # Metadata
    classification_batch_id: Optional[str] = Field(default=None)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_classified_amount: Decimal = Field(default=Decimal("0.00"))
    total_unallowable_amount: Decimal = Field(default=Decimal("0.00"))


class LineageEntry(BaseModel):
    """A single audit trail entry tracking every data transformation."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: str = Field(..., description="Action performed (import, classify, override, export, etc.)")
    actor: str = Field(default="system", description="Who performed the action (system, user_id, or 'ai')")
    entity_type: str = Field(..., description="Type of entity affected (gl_transaction, classification, export)")
    entity_id: str = Field(..., description="ID of the affected entity")
    before_state: Optional[dict] = Field(default=None, description="State before the action")
    after_state: Optional[dict] = Field(default=None, description="State after the action")
    reason: Optional[str] = Field(default=None, description="Why the action was taken")
    session_id: Optional[str] = Field(default=None, description="Processing session ID")


class ProcessingSession(BaseModel):
    """Top-level session tracking for a full cost report preparation run."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    facility_type: FacilityType
    provider_name: str = Field(default="")
    status: str = Field(default="created")  # created, importing, classifying, allocating, exporting, completed, error
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)
    ingestion_results: list[str] = Field(default_factory=list, description="IDs of ParsedIngestionResult")
    classification_batch_id: Optional[str] = Field(default=None)
    export_payload_id: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)
