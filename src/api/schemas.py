"""
FastAPI request/response Pydantic schemas for the API layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Ingestion ──────────────────────────────────────────────────────────────

class ParseRequest(BaseModel):
    """Request to parse a file that's already been uploaded."""
    file_id: str = Field(..., description="ID of the uploaded file")
    facility_type: str = Field(default="hospital", description="Facility type")
    file_type: Optional[str] = Field(default=None, description="Parser type override")


class ParseResponse(BaseModel):
    """Response after file parsing."""
    ingestion_id: str
    source_file: str
    row_count: int
    error_count: int
    column_mapping: dict
    preview: list[dict] = Field(default_factory=list, description="First 10 entries")
    processing_time_ms: float


# ── Classification ─────────────────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    """Request to run AI classification on parsed data."""
    ingestion_id: str = Field(..., description="ID from parse response")
    facility_type: str = Field(default="hospital")
    batch_size: int = Field(default=10, ge=1, le=100)


class ClassifyResponse(BaseModel):
    """Response after classification."""
    batch_id: str
    total_classified: int
    summary: dict
    results: list[dict] = Field(default_factory=list)
    processing_time_ms: float


# ── Export ─────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    """Request to generate HFS export file."""
    batch_id: str = Field(..., description="ID from classification response")
    facility_type: str = Field(default="hospital")
    provider_name: str = Field(default="")
    provider_cms_id: Optional[str] = Field(default=None)
    fiscal_year_end: Optional[str] = Field(default=None)


class ExportResponse(BaseModel):
    """Response after export generation."""
    export_id: str
    provider_name: str
    facility_type: str
    worksheet_a_count: int
    worksheet_a8_count: int
    hfs_ai_count: int
    total_classified_amount: float
    total_unallowable_amount: float
    file_path: str
    generated_at: datetime


# ── Pipeline (combined) ────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    """Run the full pipeline: upload → parse → classify → export."""
    facility_type: str = Field(default="hospital")
    provider_name: str = Field(default="Test Provider")
    provider_cms_id: Optional[str] = Field(default=None)
    fiscal_year_end: Optional[str] = Field(default=None)
    batch_size: int = Field(default=10, ge=1, le=100)


class PipelineResponse(BaseModel):
    """Full pipeline result."""
    session_id: str
    facility_type: str
    ingestion: ParseResponse
    classification: ClassifyResponse
    export: ExportResponse


# ── Health ─────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """API health check."""
    status: str = "ok"
    version: str
    timestamp: datetime
    facility_types: list[str]
