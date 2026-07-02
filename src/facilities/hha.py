"""
Home Health Agency (CMS-1728-20) Facility Registry.

Cost center definitions per PRM 15-2. HHAs track costs by discipline
(nursing, therapy, aide, etc.) with step-down allocation of overhead
costs. Some HHAs also distinguish by visit type (Medicare vs. non-Medicare).

Reference: CMS Pub. 15-2, CMS-1728-20 form instructions
"""

from __future__ import annotations

from src.core.models import AllocationMethod, CostCenterCategory, CostCenterDefinition, FacilityType
from src.facilities.base import BaseFacilityRegistry


class HHARegistry(BaseFacilityRegistry):
    """Home Health Agency — CMS-1728-20 cost center definitions."""

    facility_type = FacilityType.HHA
    form_number = "CMS-1728-20"
    form_title = "Medicare Home Health Agency Cost Report"
    cms_chapter = "PRM 15-2"
    description = "Home Health Agency (free-standing and hospital-based)"

    _general_services: dict[str, CostCenterDefinition] = {
        "01": CostCenterDefinition(
            code="01",
            name="Capital-Related Costs",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=1,
            description="Depreciation, rent, leases, taxes, insurance on buildings and equipment",
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "02": CostCenterDefinition(
            code="02",
            name="Employee Benefits",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=2,
            description="FICA, health insurance, retirement, worker's compensation",
            allocation_method=AllocationMethod.SALARIES,
        ),
        "03": CostCenterDefinition(
            code="03",
            name="Administrative & General",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=3,
            description="Administration, accounting, HR, billing, data processing, telephone, office",
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
        "04": CostCenterDefinition(
            code="04",
            name="Maintenance & Housekeeping",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=4,
            description="Building/equipment maintenance, janitorial, utilities",
            allocation_method=AllocationMethod.SQUARE_FEET,
        ),
        "05": CostCenterDefinition(
            code="05",
            name="Other General Service",
            category=CostCenterCategory.GENERAL_SERVICE,
            line_number=5,
            description="Other general service costs not classified above",
            allocation_method=AllocationMethod.ACCUMULATED_COST,
        ),
    }

    _revenue_centers: dict[str, CostCenterDefinition] = {
        # ── Direct Patient Care Disciplines ──
        "10": CostCenterDefinition(
            code="10",
            name="Skilled Nursing",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=10,
            description="RN and LPN skilled nursing visits",
            ccr_range_min=0.85,
            ccr_range_max=1.10,
        ),
        "11": CostCenterDefinition(
            code="11",
            name="Physical Therapy",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=11,
            description="Physical therapy visits",
            ccr_range_min=0.60,
            ccr_range_max=0.85,
        ),
        "12": CostCenterDefinition(
            code="12",
            name="Occupational Therapy",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=12,
            description="Occupational therapy visits",
            ccr_range_min=0.60,
            ccr_range_max=0.85,
        ),
        "13": CostCenterDefinition(
            code="13",
            name="Speech-Language Pathology",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=13,
            description="Speech-language pathology visits",
            ccr_range_min=0.60,
            ccr_range_max=0.85,
        ),
        "14": CostCenterDefinition(
            code="14",
            name="Medical Social Services",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=14,
            description="Medical social work visits",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        "15": CostCenterDefinition(
            code="15",
            name="Home Health Aide",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=15,
            description="Home health aide visits",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        # ── Supplies & Other ──
        "20": CostCenterDefinition(
            code="20",
            name="Medical Supplies",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=20,
            description="Medical supplies provided during visits",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        "21": CostCenterDefinition(
            code="21",
            name="Durable Medical Equipment",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=21,
            description="DME provided to patients",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
        "30": CostCenterDefinition(
            code="30",
            name="Other Revenue",
            category=CostCenterCategory.REVENUE_PRODUCING,
            line_number=30,
            description="Other home health revenue-producing activities",
            ccr_range_min=None,
            ccr_range_max=None,
        ),
    }

    _non_allowable: dict[str, CostCenterDefinition] = {
        "90": CostCenterDefinition(
            code="90",
            name="Non-Allowable Costs",
            category=CostCenterCategory.NON_ALLOWABLE,
            line_number=90,
            description="Marketing, lobbying, entertainment, and other non-allowable costs",
            allowable=False,
        ),
    }

    @property
    def cost_centers(self) -> dict[str, CostCenterDefinition]:
        return {**self._general_services, **self._revenue_centers, **self._non_allowable}

    @property
    def step_down_sequence(self) -> list[str]:
        """HHA step-down sequence per CMS guidelines."""
        return [
            "01",  # Capital-Related
            "02",  # Employee Benefits
            "04",  # Maintenance & Housekeeping
            "03",  # Administrative & General
            "05",  # Other General Service
        ]

    @property
    def revenue_center_codes(self) -> list[str]:
        return list(self._revenue_centers.keys())

    @property
    def general_service_codes(self) -> list[str]:
        return list(self._general_services.keys())
