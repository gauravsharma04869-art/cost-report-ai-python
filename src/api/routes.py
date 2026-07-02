"""
FastAPI route handlers for the Cost Report AI pipeline.

Endpoints:
  POST /api/v1/pipeline/run    — Full pipeline (upload → parse → classify → export)
  POST /api/v1/parse           — Parse a file only
  POST /api/v1/classify        — Classify parsed data
  POST /api/v1/export          — Generate HFS export
  GET  /api/v1/centers         — List CMS cost centers
  GET  /api/v1/lineage         — View audit trail
  GET  /api/v1/health          — Health check
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse

from src.config import settings
from src.core.models import FacilityType
from src.core.pipline import Pipeline
from src.facilities.registry import list_all_cost_centers, get_registry

from .schemas import (
    ClassifyRequest,
    ClassifyResponse,
    ExportRequest,
    ExportResponse,
    HealthResponse,
    ParseRequest,
    ParseResponse,
    PipelineRequest,
    PipelineResponse,
)

router = APIRouter(prefix="/api/v1")


# ── In-memory store for uploaded files and pipeline state ────────────
# (In production, replace with a proper database)
_upload_store: dict[str, dict[str, Any]] = {}
_pipeline_store: dict[str, dict[str, Any]] = {}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """API health check endpoint."""
    return HealthResponse(
        version=settings.APP_VERSION,
        timestamp=__import__("datetime").datetime.now(),
        facility_types=[ft.value for ft in FacilityType],
    )


@router.get("/centers")
async def list_centers(
    facility: Optional[str] = Query(None, description="Filter by facility type"),
    search: Optional[str] = Query(None, description="Search cost centers by keyword"),
):
    """List CMS cost center definitions."""
    ft = FacilityType(facility) if facility else None

    if ft:
        reg = get_registry(ft)
        result = {}
        for code, cc in sorted(reg.cost_centers.items()):
            if search and search.lower() not in cc.name.lower() and search.lower() not in cc.description.lower():
                continue
            result[code] = {
                "name": cc.name,
                "category": cc.category.value,
                "worksheet": cc.worksheet,
                "line_number": cc.line_number,
                "allowable": cc.allowable,
                "description": cc.description,
                "ccr_range": {
                    "min": cc.ccr_range_min,
                    "max": cc.ccr_range_max,
                } if cc.ccr_range_min else None,
            }
        return {
            "facility_type": ft.value,
            "form_number": reg.form_number,
            "cost_centers": result,
            "step_down_sequence": reg.step_down_sequence,
        }
    else:
        return list_all_cost_centers()


@router.post("/parse", response_model=ParseResponse)
async def parse_file(
    file: UploadFile = File(...),
    facility_type: str = Form("hospital"),
    file_type: Optional[str] = Form(None),
):
    """
    Upload and parse a file.

    Supports Excel (.xlsx, .xls), CSV, TSV, PDF, and TXT files.
    Returns structured GL entries ready for classification.
    """
    # Validate facility type
    try:
        ft = FacilityType(facility_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid facility type: {facility_type}")

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Read file content
    content = await file.read()
    if len(content) > settings.PARSER_MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max: {settings.PARSER_MAX_FILE_SIZE_MB}MB",
        )

    # Save to temp location
    suffix = Path(file.filename).suffix or ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Parse
        pipe = Pipeline(facility_type=ft)
        result = pipe.parse_file(tmp_path, file_type=file_type)

        # Store for later steps
        _pipeline_store[result.id] = {
            "ingestion": result,
            "pipeline": pipe,
        }

        # Build preview
        preview = []
        for entry in result.entries[:10]:
            preview.append({
                "account_number": entry.account_number,
                "account_description": entry.account_description,
                "debit_amount": str(entry.debit_amount),
                "credit_amount": str(entry.credit_amount),
                "net_amount": str(entry.net_amount),
            })

        return ParseResponse(
            ingestion_id=result.id,
            source_file=result.source_file,
            row_count=result.row_count,
            error_count=result.error_count,
            column_mapping=result.column_mapping,
            preview=preview,
            processing_time_ms=result.processing_time_ms,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse failed: {e}")
    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/classify", response_model=ClassifyResponse)
async def classify_entries(req: ClassifyRequest):
    """
    Run AI classification on previously parsed data.

    Maps GL accounts to CMS cost center codes using LiteLLM.
    """
    # Retrieve stored pipeline state
    pipeline_data = _pipeline_store.get(req.ingestion_id)
    if not pipeline_data:
        raise HTTPException(status_code=404, detail=f"Ingestion {req.ingestion_id} not found. Parse a file first.")

    try:
        ft = FacilityType(req.facility_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid facility type: {req.facility_type}")

    pipe: Pipeline = pipeline_data["pipeline"]
    ingestion = pipeline_data["ingestion"]

    # Reclassify with correct facility type if different
    if pipe.facility_type != ft:
        pipe = Pipeline(facility_type=ft)

    result = pipe.classify(ingestion, batch_size=req.batch_size)

    # Store classified result
    pipeline_data["classification"] = result
    pipeline_data["pipeline"] = pipe

    # Format results summary
    results_json = []
    for r in result.results:
        results_json.append({
            "account_number": r.account_number,
            "account_description": r.account_description,
            "net_amount": str(r.net_amount),
            "mapped_cost_center_code": r.mapped_cost_center_code,
            "mapped_cost_center_name": r.mapped_cost_center_name,
            "confidence_score": r.confidence_score,
            "confidence_level": r.confidence_level.value,
            "is_unallowable": r.is_unallowable,
            "reasoning": r.reasoning,
        })

    return ClassifyResponse(
        batch_id=result.id,
        total_classified=result.summary.get("total", 0),
        summary=result.summary,
        results=results_json,
        processing_time_ms=result.processing_time_ms,
    )


@router.post("/export", response_model=ExportResponse)
async def generate_export(req: ExportRequest):
    """
    Generate HFS-compatible Excel workbook from classified data.
    """
    # Find the pipeline state
    pipeline_data = None
    for pid, data in _pipeline_store.items():
        if data.get("classification") and data["classification"].id == req.batch_id:
            pipeline_data = data
            break

    if not pipeline_data:
        raise HTTPException(status_code=404, detail=f"Batch {req.batch_id} not found. Run classification first.")

    classification = pipeline_data["classification"]
    pipe: Pipeline = pipeline_data["pipeline"]

    try:
        ft = FacilityType(req.facility_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid facility type: {req.facility_type}")

    # Generate export
    output_path = settings.OUTPUT_DIR / f"export_{ft.value}_{req.batch_id[:8]}.xlsx"
    export = pipe.export(classification, output_path=output_path)

    return ExportResponse(
        export_id=export.id,
        provider_name=req.provider_name,
        facility_type=ft.value,
        worksheet_a_count=len(export.worksheet_a_rows),
        worksheet_a8_count=len(export.worksheet_a8_rows),
        hfs_ai_count=len(export.hfs_ai_rows),
        total_classified_amount=float(export.total_classified_amount),
        total_unallowable_amount=float(export.total_unallowable_amount),
        file_path=str(output_path),
        generated_at=export.generated_at,
    )


@router.post("/pipeline/run", response_model=PipelineResponse)
async def run_full_pipeline(
    file: UploadFile = File(...),
    facility_type: str = Form("hospital"),
    provider_name: str = Form("Test Provider"),
    provider_cms_id: Optional[str] = Form(None),
    fiscal_year_end: Optional[str] = Form(None),
    batch_size: int = Form(10),
):
    """
    Run the full pipeline in one call:
      1. Upload + parse file
      2. AI classification
      3. HFS Excel export

    Returns all results and the download path for the export file.
    """
    # Step 1: Parse
    content = await file.read()
    ft = FacilityType(facility_type)

    pipe = Pipeline(
        facility_type=ft,
        provider_name=provider_name,
        provider_cms_id=provider_cms_id or "",
        fiscal_year_end=fiscal_year_end or "",
    )

    suffix = Path(file.filename).suffix or ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        ingestion = pipe.parse_file(tmp_path)
    except Exception as e:
        Path(tmp_path).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Parse failed: {e}")

    Path(tmp_path).unlink(missing_ok=True)

    # Step 2: Classify
    classification = pipe.classify(ingestion, batch_size=batch_size)

    # Step 3: Export
    output_path = settings.OUTPUT_DIR / f"export_{ft.value}_{classification.id[:8]}.xlsx"
    export = pipe.export(classification, output_path=output_path)

    # Build response
    preview = []
    for entry in ingestion.entries[:10]:
        preview.append({
            "account_number": entry.account_number,
            "account_description": entry.account_description,
            "debit_amount": str(entry.debit_amount),
            "credit_amount": str(entry.credit_amount),
        })

    results_json = []
    for r in classification.results:
        results_json.append({
            "account_number": r.account_number,
            "account_description": r.account_description,
            "net_amount": str(r.net_amount),
            "mapped_cost_center_code": r.mapped_cost_center_code,
            "mapped_cost_center_name": r.mapped_cost_center_name,
            "confidence_score": r.confidence_score,
            "confidence_level": r.confidence_level.value,
            "is_unallowable": r.is_unallowable,
            "reasoning": r.reasoning,
        })

    return PipelineResponse(
        session_id=pipe.session.id,
        facility_type=ft.value,
        ingestion=ParseResponse(
            ingestion_id=ingestion.id,
            source_file=ingestion.source_file,
            row_count=ingestion.row_count,
            error_count=ingestion.error_count,
            column_mapping=ingestion.column_mapping,
            preview=preview,
            processing_time_ms=ingestion.processing_time_ms,
        ),
        classification=ClassifyResponse(
            batch_id=classification.id,
            total_classified=classification.summary.get("total", 0),
            summary=classification.summary,
            results=results_json,
            processing_time_ms=classification.processing_time_ms,
        ),
        export=ExportResponse(
            export_id=export.id,
            provider_name=provider_name,
            facility_type=ft.value,
            worksheet_a_count=len(export.worksheet_a_rows),
            worksheet_a8_count=len(export.worksheet_a8_rows),
            hfs_ai_count=len(export.hfs_ai_rows),
            total_classified_amount=float(export.total_classified_amount),
            total_unallowable_amount=float(export.total_unallowable_amount),
            file_path=str(output_path),
            generated_at=export.generated_at,
        ),
    )


@router.get("/lineage")
async def get_lineage(
    session: Optional[str] = Query(None),
    limit: int = Query(50, le=1000),
):
    """View the audit trail for a session or across all sessions."""
    from src.core.lineage import LineageLogger

    logger = LineageLogger()
    if session:
        entries = logger.get_session_trail(session)
    else:
        entries = logger.get_all_entries(limit=limit)

    return {
        "total": len(entries),
        "entries": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "action": e.action,
                "actor": e.actor,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "reason": e.reason,
            }
            for e in entries
        ],
    }


@router.get("/download/{export_id}")
async def download_export(export_id: str):
    """
    Download a generated export file by its ID.
    """
    # Look up the export file
    for pid, data in _pipeline_store.items():
        export_data = data.get("export")
        if export_data and export_data.id == export_id:
            # Find the actual file path
            for f in settings.OUTPUT_DIR.glob(f"*{export_id[:8]}*.xlsx"):
                return FileResponse(
                    path=f,
                    filename=f.name,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    raise HTTPException(status_code=404, detail=f"Export {export_id} not found or expired")
